# Nova
Cybernetic intelligence in your menu bar. (Like Siri, but doesn't suck.)
                                           
## Quickstart
Install prerequisites
```bash
# Must have homebrew installed: https://brew.sh/
# Install tools
brew install ollama ffmpeg 

# Configure ollama to run automatically
brew services start ollama 

# Install llama AI
ollama pull llama3.1:8b
```

Download [Nova.app](https://github.com/the-real-finnventor/nova/releases) and drag into ~/Applications

Run Nova or configure to run on login: `Settings > General > Login Items and Extensions > Open at Login > + > Nova.app`

## Developer instructions
Follow quickstart.prerequsites

Build
```bash
# Setup venv
python3 -m venv .venv
source .venv/bin/activate
pip3 install -r requirements.txt

# Run from terminal
python3 menu_bar.py

# Build Nova.app
pyinstaller -y Nova.spec
open dist/
```
