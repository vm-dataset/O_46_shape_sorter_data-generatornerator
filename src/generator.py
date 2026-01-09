"""
╔══════════════════════════════════════════════════════════════════════════════╗
║                    SHAPE SORTER TASK GENERATOR                                ║
║                                                                               ║
║  Generates 2D shape sorter puzzles where colored shape cards must be         ║
║  matched to their corresponding outline slots.                               ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

import math
import random
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple

from PIL import Image, ImageDraw

from core import BaseGenerator, TaskPair, ImageRenderer
from core.video_utils import VideoGenerator
from .config import TaskConfig
from .prompts import get_prompt, format_shape_summary

Canvas = Tuple[int, int]
Point = Tuple[float, float]

# Shape sorter constants
COLORS = [
    ("red", (248, 113, 113)),      # #f87171
    ("yellow", (250, 204, 21)),    # #facc15
    ("blue", (96, 165, 250)),      # #60a5fa
    ("green", (74, 222, 128)),     # #4ade80
    ("purple", (192, 132, 252)),   # #c084fc
    ("orange", (251, 146, 60)),    # #fb923c
]

SHAPES = ["circle", "square", "triangle", "star", "hexagon", "diamond"]


@dataclass
class ShapeSpec:
    """Specification for a shape card."""
    shape: str
    color_name: str
    color_rgb: Tuple[int, int, int]
    start: Point
    target: Point
    size: float

    def label(self) -> str:
        return f"{self.color_name} {self.shape}"


class ShapeSorterRenderer:
    """Renders shape sorter puzzles using PIL."""
    
    def __init__(self, canvas: Canvas):
        self.canvas = canvas
        self.bg_color = (248, 250, 252)  # #f8fafc
        self.divider_color = (148, 163, 184)  # #94a3b8
        self.outline_color = (100, 116, 139)  # #64748b
    
    def render_start(self, specs: Sequence[ShapeSpec]) -> Image.Image:
        """Render initial state: cards on left, outlines on right."""
        img = Image.new('RGB', self.canvas, self.bg_color)
        draw = ImageDraw.Draw(img)
        
        self._draw_layout(draw)
        
        # Draw outlines first (so cards appear on top)
        for spec in specs:
            self._draw_shape(draw, spec.target, spec.size, spec.shape, 
                           self.outline_color, filled=False, linewidth=3)
        
        # Draw filled cards
        for spec in specs:
            self._draw_shape(draw, spec.start, spec.size, spec.shape, 
                           spec.color_rgb, filled=True)
        
        return img
    
    def render_end(self, specs: Sequence[ShapeSpec]) -> Image.Image:
        """Render final state: all cards in their slots."""
        img = Image.new('RGB', self.canvas, self.bg_color)
        draw = ImageDraw.Draw(img)
        
        self._draw_layout(draw)
        
        # Draw filled cards in target positions
        for spec in specs:
            self._draw_shape(draw, spec.target, spec.size, spec.shape, 
                           spec.color_rgb, filled=True)
        
        return img
    
    def _draw_layout(self, draw: ImageDraw.Draw) -> None:
        """Draw the board layout with divider."""
        w, h = self.canvas
        # Draw divider line (semi-transparent effect by using lighter color)
        divider_x = w * 0.5
        divider_width = 8
        # Blend divider color with background for semi-transparent effect
        divider_rgb = tuple(
            int(self.bg_color[i] * 0.65 + self.divider_color[i] * 0.35)
            for i in range(3)
        )
        draw.rectangle(
            [(divider_x - divider_width // 2, 40), 
             (divider_x + divider_width // 2, h - 40)],
            fill=divider_rgb
        )
    
    def _draw_shape(
        self,
        draw: ImageDraw.Draw,
        center: Point,
        size: float,
        shape: str,
        color: Tuple[int, int, int] | Tuple[int, int, int, int],
        filled: bool,
        linewidth: float = 2.5,
    ) -> None:
        """Draw a shape at the given center position."""
        x, y = center
        
        if shape == "circle":
            bbox = [x - size/2, y - size/2, x + size/2, y + size/2]
            if filled:
                draw.ellipse(bbox, fill=color)
            else:
                draw.ellipse(bbox, outline=color, width=int(linewidth))
        
        elif shape == "square":
            bbox = [x - size/2, y - size/2, x + size/2, y + size/2]
            if filled:
                draw.rectangle(bbox, fill=color)
            else:
                draw.rectangle(bbox, outline=color, width=int(linewidth))
        
        elif shape == "triangle":
            points = [
                (x, y - size/2),
                (x - size/2, y + size/2),
                (x + size/2, y + size/2),
            ]
            if filled:
                draw.polygon(points, fill=color)
            else:
                draw.polygon(points, outline=color, width=int(linewidth))
        
        elif shape == "hexagon":
            points = []
            for i in range(6):
                angle = math.pi / 6 + i * math.pi / 3
                px = x + (size/2) * math.cos(angle)
                py = y + (size/2) * math.sin(angle)
                points.append((px, py))
            if filled:
                draw.polygon(points, fill=color)
            else:
                draw.polygon(points, outline=color, width=int(linewidth))
        
        elif shape == "diamond":
            points = [
                (x, y - size/2),
                (x + size/2, y),
                (x, y + size/2),
                (x - size/2, y),
            ]
            if filled:
                draw.polygon(points, fill=color)
            else:
                draw.polygon(points, outline=color, width=int(linewidth))
        
        elif shape == "star":
            points = []
            for i in range(10):
                angle = math.pi / 2 + i * math.pi / 5
                r = (size/2) if i % 2 == 0 else (size/2) * 0.45
                px = x + r * math.cos(angle)
                py = y + r * math.sin(angle)
                points.append((px, py))
            if filled:
                draw.polygon(points, fill=color)
            else:
                draw.polygon(points, outline=color, width=int(linewidth))
        
        else:
            raise ValueError(f"Unsupported shape type: {shape}")


class TaskGenerator(BaseGenerator):
    """
    Shape Sorter task generator.
    
    Generates puzzles where colored shape cards must be matched to outline slots.
    """
    
    def __init__(self, config: TaskConfig):
        super().__init__(config)
        self.renderer = ShapeSorterRenderer(canvas=config.image_size)
        self._seen_signatures: set[str] = set()
        
        # Initialize video generator if enabled
        self.video_generator = None
        if config.generate_videos and VideoGenerator.is_available():
            self.video_generator = VideoGenerator(fps=config.video_fps, output_format="mp4")
    
    def generate_task_pair(self, task_id: str) -> TaskPair:
        """Generate one shape sorter task pair."""
        
        # Generate task data
        difficulty = self.config.difficulty or "medium"
        task_data = self._generate_task_data(difficulty)
        
        # Render images
        first_image = self.renderer.render_start(task_data["specs"])
        final_image = self.renderer.render_end(task_data["specs"])
        
        # Generate video (optional)
        video_path = None
        if self.config.generate_videos and self.video_generator:
            video_path = self._generate_video(
                first_image, final_image, task_id, task_data
            )
        
        # Generate prompt
        shape_labels = [spec.label() for spec in task_data["specs"]]
        prompt = get_prompt(shape_labels)
        
        return TaskPair(
            task_id=task_id,
            domain=self.config.domain,
            prompt=prompt,
            first_image=first_image,
            final_image=final_image,
            ground_truth_video=video_path
        )
    
    # ══════════════════════════════════════════════════════════════════════════
    #  TASK GENERATION
    # ══════════════════════════════════════════════════════════════════════════
    
    def _generate_task_data(self, difficulty: str) -> dict:
        """Generate shape sorter task data."""
        num_shapes = self._shape_count_for_difficulty(difficulty)
        
        # Try to generate unique task
        for attempt in range(25):
            specs, layout_variant = self._create_specs(num_shapes)
            signature = self._build_signature(specs, layout_variant)
            
            if signature not in self._seen_signatures:
                self._seen_signatures.add(signature)
                return {
                    "specs": specs,
                    "layout_variant": layout_variant,
                    "difficulty": difficulty,
                    "num_shapes": num_shapes,
                }
        
        # If we couldn't generate unique, use the last one
        specs, layout_variant = self._create_specs(num_shapes)
        return {
            "specs": specs,
            "layout_variant": layout_variant,
            "difficulty": difficulty,
            "num_shapes": num_shapes,
        }
    
    def _shape_count_for_difficulty(self, difficulty: str) -> int:
        """Get number of shapes based on difficulty."""
        if difficulty == "easy":
            return random.randint(2, 3)
        elif difficulty == "hard":
            return random.randint(5, 6)
        else:  # medium
            return random.randint(3, 5)
    
    def _create_specs(self, count: int) -> Tuple[List[ShapeSpec], str]:
        """Create shape specifications."""
        layout_variant = self._choose_layout(count)
        w, h = self.canvas
        
        # Generate card positions (left side)
        cards, card_size = self._generate_positions(
            count=count,
            columns=self._layout_columns(layout_variant, side="cards"),
            x_range=(0.12 * w, 0.4 * w),
            y_range=(0.18 * h, 0.82 * h),
            jitter=self._layout_jitter(layout_variant, side="cards"),
        )
        
        # Generate slot positions (right side)
        slots, slot_size = self._generate_positions(
            count=count,
            columns=self._layout_columns(layout_variant, side="slots"),
            x_range=(0.6 * w, 0.88 * w),
            y_range=(0.18 * h, 0.82 * h),
            jitter=self._layout_jitter(layout_variant, side="slots"),
        )
        
        size = min(card_size, slot_size)
        shapes = self._sample_shapes(count)
        colors = self._sample_colors(count)
        
        specs: List[ShapeSpec] = []
        for i in range(count):
            color_name, color_rgb = colors[i]
            specs.append(
                ShapeSpec(
                    shape=shapes[i],
                    color_name=color_name,
                    color_rgb=color_rgb,
                    start=cards[i],
                    target=slots[i],
                    size=size,
                )
            )
        
        return specs, layout_variant
    
    def _sample_shapes(self, count: int) -> List[str]:
        """Sample shapes without replacement if possible."""
        if count <= len(SHAPES):
            return random.sample(SHAPES, k=count)
        base = random.sample(SHAPES, k=len(SHAPES))
        base += random.choices(SHAPES, k=count - len(SHAPES))
        return base
    
    def _sample_colors(self, count: int) -> List[Tuple[str, Tuple[int, int, int]]]:
        """Sample colors without replacement if possible."""
        if count <= len(COLORS):
            return random.sample(COLORS, k=count)
        colors = random.sample(COLORS, k=len(COLORS))
        colors += random.choices(COLORS, k=count - len(COLORS))
        return colors
    
    def _choose_layout(self, count: int) -> str:
        """Choose layout variant based on shape count."""
        if count <= 2:
            return "line"
        elif count == 3:
            return "staggered"
        elif count == 4:
            return "grid"
        else:
            return "scatter"
    
    def _layout_columns(self, layout: str, side: str) -> int:
        """Get number of columns for layout."""
        base = {
            "line": 1,
            "staggered": 2 if side == "cards" else 1,
            "grid": 2,
            "scatter": 2,
        }
        return base.get(layout, 1)
    
    def _layout_jitter(self, layout: str, side: str) -> float:
        """Get jitter amount for layout."""
        jitter_map = {
            "line": 0.0,
            "staggered": 0.015 if side == "cards" else 0.0,
            "grid": 0.01,
            "scatter": 0.03 if side == "cards" else 0.015,
        }
        return jitter_map.get(layout, 0.0)
    
    def _generate_positions(
        self,
        count: int,
        columns: int,
        x_range: Tuple[float, float],
        y_range: Tuple[float, float],
        jitter: float = 0.0,
    ) -> Tuple[List[Point], float]:
        """Generate positions for shapes."""
        columns = max(1, columns)
        rows = math.ceil(count / columns)
        positions: List[Point] = []
        
        for idx in range(count):
            row = idx // columns
            col = idx % columns
            x = x_range[0] + (col + 0.5) / columns * (x_range[1] - x_range[0])
            y = y_range[0] + (row + 0.5) / rows * (y_range[1] - y_range[0])
            
            if jitter > 0:
                x += random.uniform(-jitter, jitter) * (x_range[1] - x_range[0])
                y += random.uniform(-jitter, jitter) * (y_range[1] - y_range[0])
            
            positions.append((x, y))
        
        cell_w = (x_range[1] - x_range[0]) / columns
        cell_h = (y_range[1] - y_range[0]) / rows
        size = min(90.0, cell_w * 0.55, cell_h * 0.55)
        
        return positions, size
    
    def _build_signature(self, specs: Sequence[ShapeSpec], layout_variant: str) -> str:
        """Build signature for uniqueness checking."""
        quantized = []
        for spec in specs:
            quantized.append((
                spec.shape,
                spec.color_name,
                round(spec.start[0], 1),
                round(spec.start[1], 1),
                round(spec.target[0], 1),
                round(spec.target[1], 1),
                round(spec.size, 1),
            ))
        quantized.sort()
        return f"{layout_variant}|{len(specs)}|" + "|".join(
            ",".join(map(str, item)) for item in quantized
        )
    
    @property
    def canvas(self) -> Canvas:
        """Get canvas size from config."""
        return self.config.image_size
    
    # ══════════════════════════════════════════════════════════════════════════
    #  VIDEO GENERATION
    # ══════════════════════════════════════════════════════════════════════════
    
    def _generate_video(
        self,
        first_image: Image.Image,
        final_image: Image.Image,
        task_id: str,
        task_data: dict
    ) -> Optional[str]:
        """Generate ground truth video with cards sliding smoothly."""
        temp_dir = Path(tempfile.gettempdir()) / f"{self.config.domain}_videos"
        temp_dir.mkdir(parents=True, exist_ok=True)
        video_path = temp_dir / f"{task_id}_ground_truth.mp4"
        
        # Create animation frames with dynamic frame calculation
        num_cards = len(task_data["specs"])
        max_frames = int(self.config.max_video_duration * self.config.video_fps)
        hold_frames = 3
        # Calculate transition_frames to ensure video stays under max duration
        # Total frames = 2 * hold_frames + num_cards * transition_frames
        # transition_frames = (max_frames - 2 * hold_frames) / num_cards
        available_frames = max_frames - 2 * hold_frames
        transition_frames = max(10, int(available_frames / num_cards))
        
        frames = self._create_animation_frames(
            task_data["specs"],
            hold_frames=hold_frames,
            transition_frames=transition_frames
        )
        
        result = self.video_generator.create_video_from_frames(
            frames,
            video_path
        )
        
        return str(result) if result else None
    
    def _create_animation_frames(
        self,
        specs: Sequence[ShapeSpec],
        hold_frames: int = 5,
        transition_frames: int = 25
    ) -> List[Image.Image]:
        """
        Create animation frames where cards slide smoothly from start to target.
        
        Cards move one at a time, sliding smoothly without teleportation.
        """
        frames = []
        original_specs = list(specs)  # Keep original specs for reference
        
        # Render initial state
        first_frame = self.renderer.render_start(specs)
        
        # Hold initial position
        for _ in range(hold_frames):
            frames.append(first_frame.copy())
        
        # Animate each card moving one at a time
        for card_idx, original_spec in enumerate(original_specs):
            # For each card, create transition frames
            for i in range(transition_frames):
                progress = i / (transition_frames - 1) if transition_frames > 1 else 1.0
                
                # Calculate current position for this card
                current_x = original_spec.start[0] + (original_spec.target[0] - original_spec.start[0]) * progress
                current_y = original_spec.start[1] + (original_spec.target[1] - original_spec.start[1]) * progress
                
                # Render frame: cards that have already moved are at target,
                # current card is at intermediate position, others are at start
                frame = self._render_animation_frame(
                    original_specs, card_idx, (current_x, current_y)
                )
                frames.append(frame)
        
        # Render final state
        final_frame = self.renderer.render_end(specs)
        
        # Hold final position
        for _ in range(hold_frames):
            frames.append(final_frame.copy())
        
        return frames
    
    def _render_animation_frame(
        self,
        original_specs: Sequence[ShapeSpec],
        moving_card_idx: int,
        current_pos: Point
    ) -> Image.Image:
        """Render a single animation frame."""
        img = Image.new('RGB', self.canvas, self.renderer.bg_color)
        draw = ImageDraw.Draw(img)
        
        # Draw layout
        self.renderer._draw_layout(draw)
        
        # Draw outlines for all slots
        for spec in original_specs:
            self.renderer._draw_shape(
                draw, spec.target, spec.size, spec.shape,
                self.renderer.outline_color, filled=False, linewidth=3
            )
        
        # Draw cards: already moved cards at target, moving card at intermediate, others at start
        for idx, spec in enumerate(original_specs):
            if idx < moving_card_idx:
                # Already moved: draw at target
                pos = spec.target
            elif idx == moving_card_idx:
                # Currently moving: draw at current intermediate position
                pos = current_pos
            else:
                # Not yet moved: draw at start
                pos = spec.start
            
            self.renderer._draw_shape(
                draw, pos, spec.size, spec.shape,
                spec.color_rgb, filled=True
            )
        
        return img
