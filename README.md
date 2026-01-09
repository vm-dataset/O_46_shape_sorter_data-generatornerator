# Shape Sorter Task Data Generator 🎯

A data generator for creating 2D shape sorter reasoning tasks. Generates puzzles where colored shape cards must be matched to their corresponding outline slots, evaluating spatial reasoning and planning abilities in video generation models.

This task generator follows the [template-data-generator](https://github.com/vm-dataset/template-data-generator.git) format and is compatible with [VMEvalKit](https://github.com/Video-Reason/VMEvalKit.git).

Repository: [O_46_shape_sorter_data-generatornerator](https://github.com/vm-dataset/O_46_shape_sorter_data-generatornerator)

---

## 🚀 Quick Start

```bash
# 1. Clone the repository
git clone https://github.com/vm-dataset/O_46_shape_sorter_data-generatornerator.git
cd O_46_shape_sorter_data-generatornerator

# 2. Create and activate virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# 3. Install dependencies
pip install --upgrade pip
pip install -r requirements.txt
pip install -e .

# 4. Generate tasks
python3 examples/generate.py --num-samples 50
```

---

## 📁 Structure

```
shape-sorter-task-data-generator/
├── core/                    # ✅ Framework utilities (DO NOT MODIFY)
│   ├── base_generator.py     # Abstract base class
│   ├── schemas.py            # Pydantic models
│   ├── image_utils.py        # Image helpers
│   ├── video_utils.py        # Video generation
│   └── output_writer.py       # File output
├── src/                      # ⚠️ Shape Sorter task implementation
│   ├── generator.py          # Shape sorter generator
│   ├── prompts.py            # Prompt templates
│   └── config.py             # Configuration
├── examples/
│   └── generate.py           # Entry point
└── data/questions/           # Generated output
```

---

## 📦 Output Format

Every generator produces:

```
data/questions/shape_sorter_task/{task_id}/
├── first_frame.png          # Initial state: cards on left, outlines on right
├── final_frame.png          # Goal state: all cards in matching slots
├── prompt.txt               # Instructions (REQUIRED)
└── ground_truth.mp4         # Solution video (OPTIONAL)
```

---

## 🎨 Task Description

The Shape Sorter task evaluates whether video generation models can plan and execute multi-step shape matching actions from a fixed top-down perspective. Each task consists of:

- **Shapes**: 6 types (circle, square, triangle, star, hexagon, diamond)
- **Colors**: 6 high-contrast colors (red, yellow, blue, green, purple, orange)
- **Layout**: 4 variants (line, staggered, grid, scatter)
- **Difficulty**: Easy (2-3 shapes), Medium (3-5 shapes), Hard (5-6 shapes)

The task requires models to:
1. Identify matching shapes and colors
2. Plan the sequence of moves
3. Animate smooth sliding motions (no teleportation)
4. Maintain fixed top-down camera view

---

## ⚙️ Configuration

### Task-Specific Settings (`src/config.py`)

```python
class TaskConfig(GenerationConfig):
    domain: str = Field(default="shape_sorter")
    image_size: tuple[int, int] = Field(default=(768, 512))
    
    generate_videos: bool = Field(default=True)
    video_fps: int = Field(default=10)
    
    difficulty: Optional[str] = Field(default=None)  # "easy", "medium", "hard"
```

### Generation Options

```bash
# Generate 10 tasks with default settings
python3 examples/generate.py --num-samples 10

# Generate tasks without videos (faster)
python3 examples/generate.py --num-samples 10 --no-videos

# Generate with custom output directory
python3 examples/generate.py --num-samples 10 --output data/my_output

# Generate with random seed for reproducibility
python3 examples/generate.py --num-samples 10 --seed 42
```

---

## 🎬 Video Generation

The generator creates smooth animations where cards slide one at a time from their starting positions to matching outline slots. Each card moves smoothly without teleportation, maintaining visual continuity.

**Note**: Video generation requires `opencv-python`. Install with:
```bash
pip install opencv-python
```

---

## 📊 Task Features

- **6 Shape Types**: Circle, Square, Triangle, Star, Hexagon, Diamond
- **6 Colors**: Red, Yellow, Blue, Green, Purple, Orange
- **4 Layout Variants**: Line, Staggered, Grid, Scatter
- **3 Difficulty Levels**: Easy (2-3 shapes), Medium (3-5 shapes), Hard (5-6 shapes)
- **Automatic Uniqueness**: Prevents duplicate task generation
- **VMEvalKit Compatible**: Output format matches VMEvalKit standards

---

## 🔧 Customization

The generator is built on a flexible framework. Key files:

- **`src/generator.py`**: Core generation logic, shape rendering, animation
- **`src/prompts.py`**: Prompt templates and shape summary formatting
- **`src/config.py`**: Configuration and hyperparameters

---

## 📝 Example Output

Each generated task includes:
- **first_frame.png**: Colored cards staged on left, outline slots on right
- **final_frame.png**: All cards placed in matching slots
- **prompt.txt**: Instruction text (e.g., "Move each colored shape card from the left staging area into its matching outline on the right...")
- **ground_truth.mp4**: Smooth animation showing cards sliding into place

---

## 🎯 Use Cases

- Evaluating video generation model reasoning abilities
- Training spatial reasoning datasets
- Benchmarking multi-step planning capabilities
- Testing object matching and manipulation understanding

---

## 📄 License

See LICENSE file for details.

---

**Single entry point:** `python3 examples/generate.py --num-samples 50`
