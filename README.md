# PowerPoint Generator 📊

![Version](https://img.shields.io/badge/version-1.0.0-blue.svg)
![Python](https://img.shields.io/badge/python-3.8+-green.svg)
![License](https://img.shields.io/badge/license-MIT-orange.svg)
![Status](https://img.shields.io/badge/status-stable-success.svg)

A Flask-based web application that generates PowerPoint presentations from JSON data. Create professional presentations programmatically with customizable slides, content blocks, images, and formatting.

**Created by Shubham Shah** | [GitHub](https://github.com/bornebyte) | [LinkedIn](https://www.linkedin.com/in/bornebyte/) | [Email](mailto:shahshubham1888@gmail.com)

---

## 📚 Documentation

- **[Platform Guide](PLATFORM_GUIDE.md)** - Detailed Windows/macOS/Linux installation
- **[Quick Start Guide](QUICKSTART.md)** - Get started in 5 minutes
- **[Enhanced Features Guide](FEATURES.md)** - Complete guide to all formatting and styling options
- **[Deployment Guide](DEPLOYMENT.md)** - Production deployment instructions
- **[Contributing Guide](CONTRIBUTING.md)** - How to contribute
- **[Project Summary](PROJECT_SUMMARY.md)** - Complete overview of the project

## ✨ Features

### Core Features
- 🎨 **Web Interface**: User-friendly web UI for generating presentations
- 📝 **JSON-Driven**: Define your entire presentation structure in JSON
- 🔌 **Remote MCP Server**: Connect ChatGPT, Claude, and other MCP clients to generate presentations and receive a direct download link
- 🤖 **AI Helper**: Dynamic prompt generator - enter topic and number of slides, get customized prompt for ChatGPT/Claude
- 🎓 **College/University Support**: Customizable title slides for academic presentations
  - Works with any college or university
  - Single student presentations with details
  - Group projects with student tables
  - Add your own college logo
- 🚀 **Production Ready**: Includes Gunicorn for production deployment
- 🔧 **Easy Setup**: One-command installation script
- 🌟 **Open Source**: Free to use, modify, and distribute

### Rich Formatting Features (NEW! ⭐)
- **📋 Headings**: 3 levels with custom colors and alignment
- **✏️ Styled Paragraphs**: Size, color, bold, italic, alignment options
- **🔹 Enhanced Bullets**: Colored, styled bullets with nested sub-points
- **🔢 Numbered Lists**: Sequential lists with custom styling
- **📊 Tables**: Professional data tables with headers, colors, and custom sizing
- **📦 Text Boxes**: Positioned boxes with backgrounds for highlights and emphasis
- **🎨 Colors**: Support for named colors, hex codes, and RGB values
- **🖼️ Images**: Row, column, and grid layouts
- **🎯 All Optional**: Every formatting property is optional - use what you need

See the [Enhanced Features Guide](FEATURES.md) for detailed documentation and examples.

## 🚀 Quick Install

### One-Line Installation

**Linux / macOS:**
```bash
curl -sSL https://raw.githubusercontent.com/bornebyte/ppt-generator/main/install.sh | bash
```

**Windows (Command Prompt):**
```cmd
curl -o install.bat https://raw.githubusercontent.com/bornebyte/ppt-generator/main/install.bat && install.bat
```

**Windows (PowerShell):**
```powershell
Invoke-WebRequest -Uri "https://raw.githubusercontent.com/bornebyte/ppt-generator/main/install.ps1" -OutFile "install.ps1"; powershell -ExecutionPolicy Bypass -File install.ps1
```

This will:
- Clone the repository
- Set up a virtual environment
- Install all dependencies
- Create a launcher command for easy access

### After Installation

**Linux / macOS:**
```bash
pptgen        # Start the development server
pptgen -p     # Start with production server (Gunicorn)
```

**Windows:**
```cmd
pptgen.bat        # Start the development server
pptgen.bat -p     # Start with production server
```

Or use the universal Python launcher (all platforms):
```bash
python pptgen-launcher.py
python pptgen-launcher.py -p
```

## 📦 Manual Installation

### Prerequisites

- Python 3.8 or higher
- pip (Python package installer)
- Git

### Step-by-Step Setup

1. **Clone the repository**
   ```bash
   git clone https://github.com/bornebyte/ppt-generator.git
   cd ppt-generator
   ```

2. **Create a virtual environment**
   
   **Linux / macOS:**
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```
   
   **Windows (Command Prompt):**
   ```cmd
   python -m venv venv
   venv\Scripts\activate.bat
   ```
   
   **Windows (PowerShell):**
   ```powershell
   python -m venv venv
   .\venv\Scripts\Activate.ps1
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Run the application**
   
   **Development mode:**
   
   *Linux / macOS:*
   ```bash
   ./pptgen
   # or
   python main.py
   ```
   
   *Windows:*
   ```cmd
   pptgen.bat
   REM or
   python main.py
   ```
   
   **Production mode:**
   
   *Linux / macOS:*
   ```bash
   ./pptgen -p
   # or
   gunicorn -w 4 -b 0.0.0.0:5000 main:app
   ```
   
   *Windows:*
   ```cmd
   pptgen.bat -p
   REM or
   python -m gunicorn -w 4 -b 0.0.0.0:5000 main:app
   ```

5. **Open your browser**
   ```
   http://localhost:5000
   ```

## 🎯 Usage

### Using the Web Interface

1. Open the application in your browser
2. **(Optional) Enable Jain University mode** for academic presentations
   - Toggle "Create for JAIN University"
   - Enter presentation title
   - Choose single student or group project
   - Fill in student details (name, USN, course, semester)
   - Enter professor name (submitted to)
3. **Get JSON from AI** (if needed):
   - Click "Copy Prompt" in the AI Helper section
   - Paste into ChatGPT, Claude, or any AI assistant
   - Replace "[YOUR TOPIC]" with your actual topic
   - Copy the generated JSON
4. Enter a filename for your presentation
5. Paste your JSON content
6. Click "Generate PPT"
7. Download your generated PowerPoint file

### JSON Format

Here's a basic structure for your presentation:

```json
{
    "meta": {
        "title": "Your Presentation Title",
        "subtitle": "Your Subtitle",
        "author": "Your Name",
        "institution": "Your Institution"
    },
    "slides": [
        {
            "type": "title"
        },
        {
            "type": "content",
            "title": "Slide Title",
            "subtitle": "Optional Subtitle",
            "blocks": [
                {
                    "kind": "paragraph",
                    "text": "Your paragraph text here."
                },
                {
                    "kind": "bullets",
                    "items": [
                        "Bullet point 1",
                        "Bullet point 2",
                        {
                            "text": "Bullet with sub-points",
                            "subpoints": [
                                "Sub-point 1",
                                "Sub-point 2"
                            ]
                        }
                    ]
                }
            ],
            "notes": "Speaker notes for this slide"
        }
    ]
}
```

### Content Block Types

#### 1. Paragraph Block
```json
{
    "kind": "paragraph",
    "text": "Your paragraph text here."
}
```

#### 2. Bullets Block
```json
{
    "kind": "bullets",
    "items": [
        "Simple bullet point",
        {
            "text": "Bullet with sub-points",
            "subpoints": ["Sub 1", "Sub 2"]
        }
    ]
}
```

#### 3. Images Block
```json
{
    "kind": "images",
    "layout": "row",
    "items": [
        {
            "path": "path/to/image.png",
            "caption": "Image caption"
        }
    ]
}
```

Available layouts: `row`, `column`, `grid`

## 📁 Project Structure

```
ppt-generator/
├── main.py              # Flask application
├── requirements.txt     # Python dependencies
├── content.json        # Example JSON content
├── install.sh          # Installation script
├── pptgen              # CLI executable
├── templates/
│   ├── base.html       # Base template
│   └── index.html      # Main page
├── static/
│   └── css/
│       └── style.css   # Custom styles
└── README.md           # Documentation
```

## 🔧 Configuration

### Environment Variables

You can configure the application using environment variables:

```bash
export FLASK_APP=main.py
export FLASK_ENV=development  # or production
export PORT=5000              # Default port
export PUBLIC_BASE_URL=https://your-domain.example  # Public URL used in MCP download links
```

For browser-based MCP clients, optionally set `MCP_ALLOWED_ORIGINS` to a comma-separated list of exact origins. ChatGPT and Claude web origins are allowed by default. The `/mcp` endpoint reuses the same generation and analytics flow as the web app; MCP PPTX artifacts are stored in the configured SQL database so their download links work across app workers and restarts.

### Production Deployment

For production deployment, use Gunicorn:

```bash
gunicorn -w 4 -b 0.0.0.0:5000 main:app
```

Options:
- `-w 4`: Number of worker processes
- `-b 0.0.0.0:5000`: Bind to all interfaces on port 5000
- `--timeout 120`: Request timeout in seconds

## 🛠️ API Endpoints

### `GET /`
Home page with the web interface.

### `POST /generate_ppt`
Generate a PowerPoint presentation.

**Request Body:**
```json
{
    "file_name": "my_presentation",
    "json_data": "{...JSON content...}"
}
```

**Response:**
- Success: PowerPoint file download
- Error: JSON with error message and status code

### `POST /mcp`

Stateless Streamable HTTP MCP endpoint. Connect an online MCP client to `https://your-domain.example/mcp`, then call the `generate_ppt` tool with a `presentation` object containing `meta` and `slides`. It returns a download link and a structured result containing the file name, generation ID, and URL. MCP generations are recorded in the existing generations/students tables; downloadable PPTX files are persisted in the additive `generated_files` table.

The generated link uses `PUBLIC_BASE_URL` when configured. Set this to the externally reachable HTTPS base URL when running behind a reverse proxy or hosting platform. The download remains available while its database record is retained.

Example tool arguments:

```json
{
  "file_name": "quarterly-review",
  "presentation": {
    "meta": {"title": "Quarterly Review", "subtitle": "Q3 results"},
    "slides": [
      {
        "type": "content",
        "title": "Highlights",
        "blocks": [{"kind": "bullets", "items": ["Revenue grew 12%", "Retention improved"]}]
      }
    ]
  }
}
```

The endpoint accepts MCP 2025 Streamable HTTP clients and the 2026-07-28 request-metadata format. Configure a persistent `DATABASE_URL` for hosted deployments so analytics and generated downloads survive restarts. The existing Docker Compose setup stores both in the mounted `instance` database.

## 🧪 Example

See [`content.json`](content.json) for a complete example presentation about "Metals in Mobile Phones".

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## 📝 License

This project is open source and available under the [MIT License](LICENSE).

## 🐛 Troubleshooting

### Platform-Specific Issues

See the [Platform Guide](PLATFORM_GUIDE.md) for detailed platform-specific troubleshooting.

### Installation Timeout/Network Issues

If installation fails with timeout errors:

```bash
# Manual installation with increased timeout
cd ~/.ppt-generator  # or your install directory
source venv/bin/activate
pip install --timeout 300 -r requirements.txt

# Or try with retry
pip install --timeout 300 --retries 5 -r requirements.txt
```

### "Package not found" Error

If you encounter `Package not found at '.../pptx/templates/default.pptx'`:

```bash
pip uninstall python-pptx
pip install python-pptx
```

### Port Already in Use

If port 5000 is already in use:

```bash
# Change port
export PORT=8000
python main.py
```

Or kill the existing process:
```bash
lsof -ti:5000 | xargs kill -9
```

### Virtual Environment Issues

If you have issues with the virtual environment:

```bash
rm -rf venv
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

## 📧 Support

If you have any questions or run into issues, please open an issue on GitHub or reach out to the creator.

## 👨‍💻 About the Creator

**Shubham Shah** is the creator and maintainer of this project. 

- 🐙 **GitHub**: [@bornebyte](https://github.com/bornebyte)
- 💼 **LinkedIn**: [Shubham Shah](https://www.linkedin.com/in/bornebyte/)
- 📧 **Email**: [shahshubham1888@gmail.com](mailto:shahshubham1888@gmail.com)

This project was created to help students and professionals easily generate presentations. Feel free to use it, contribute, or reach out with suggestions!

### Contributing

Contributions are welcome! Please feel free to submit a Pull Request. For major changes, please open an issue first to discuss what you would like to change.

## 🙏 Acknowledgments

- Built with [python-pptx](https://python-pptx.readthedocs.io/)
- Flask web framework
- Originally created for educational purposes
- Made open-source for everyone to benefit
- Bootstrap for UI components

---

Made with ❤️ by the PPT Generator team
