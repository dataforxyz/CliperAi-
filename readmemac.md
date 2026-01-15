# macOS Notes

## TUI Copy Logs Feature

The "Copy Logs" feature (button or `l` key) uses the OSC 52 terminal escape sequence to copy text to your clipboard.

**Supported terminals:**
- iTerm2
- WezTerm
- Kitty
- Alacritty
- Hyper

**Not supported:**
- macOS Terminal.app (the built-in terminal does not support OSC 52)

If you're using Terminal.app and need to copy logs, consider switching to iTerm2 or another supported terminal emulator.
