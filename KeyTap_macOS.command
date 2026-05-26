#!/usr/bin/env bash
# ==================================================================
#          KEYTAP - THE CHAOS SOUND KEYBOARD (macOS Loader)
# ==================================================================
# Double-click this script in Finder to launch KeyTap on macOS!

# Get the directory where this script is located and change to it
CDIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$CDIR"

clear
echo "=================================================================="
echo "          KEYTAP - THE CHAOS SOUND KEYBOARD (macOS Loader)        "
echo "=================================================================="
echo ""

# 1. Verify Python 3 is installed
if ! command -v python3 &> /dev/null
then
    echo "❌ [ERROR] Python 3 is not installed on this Mac!"
    echo "Please download and install Python 3 from: https://www.python.org/downloads/"
    echo ""
    echo "Press Enter to exit..."
    read -r
    exit 1
fi

echo "✅ [SYSTEM] Python 3 detected: $(python3 --version)"

# 2. Verify and install libraries on the fly
echo "[SYSTEM] Verifying Python library dependencies..."
for pkg in customtkinter pygame pynput; do
    python3 -c "import $pkg" &> /dev/null
    if [ $? -ne 0 ]; then
        echo "⏳ [BOOT] Library '$pkg' is missing. Installing..."
        python3 -m pip install "$pkg" --quiet
        if [ $? -ne 0 ]; then
            echo "⚠️ [BOOT] Direct pip failed, trying pip3..."
            pip3 install "$pkg" --quiet
        fi
    else
        echo "✅ [BOOT] Library '$pkg' is already installed."
    fi
done

echo ""
echo "------------------------------------------------------------------"
echo "🔒 CRITICAL MAC PRIVACY PERMISSION NOTE:"
echo "Because KeyTap runs system-wide in the background, macOS requires"
echo "you to grant Accessibility or Input Monitoring access to Terminal."
echo ""
echo "👉 Go to: System Settings -> Privacy & Security -> Input Monitoring"
echo "   and make sure 'Terminal' is checked/enabled!"
echo "------------------------------------------------------------------"
echo ""
echo "🚀 [SYSTEM] Launching KeyTap dashboard..."
echo "Close the KeyTap GUI window or press Ctrl+C in this Terminal to exit."
echo ""

python3 audio_keyboard.py
