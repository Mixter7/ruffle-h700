pub const BUTTONS: &[(&str, Button, &str)] = &[
    ("A", Button::B, "X"),
    ("B", Button::A, "Z"),
    ("X", Button::Y, "A"),
    ("Y", Button::X, "S"),
    ("L", Button::LeftShoulder, "Space"),
    ("R", Button::RightShoulder, "C"),
    ("L2", Button::Paddle1, "W"),
    ("R2", Button::Paddle2, "S"),
    ("L3", Button::LeftStick, "O"),
    ("R3", Button::RightStick, "L"),
    ("Up", Button::DPadUp, "Up"),
    ("Down", Button::DPadDown, "Down"),
    ("Left", Button::DPadLeft, "Left"),
    ("Right", Button::DPadRight, "Right"),
    ("Select", Button::Back, "Backspace"),
    ("Start", Button::Start, "Return"),
];
pub const KEYS: &[&str] = &["A", "B", "C", "D", "E", "F", "G", "H", "I", "J", "K", "L", "M", "N", "O", "P", "Q", "R", "S", "T", "U", "V", "W", "X", "Y", "Z", "Num0", "Num1", "Num2", "Num3", "Num4", "Num5", "Num6", "Num7", "Num8", "Num9", "Up", "Down", "Left", "Right", "Space", "Return", "Enter", "Escape", "Esc", "Tab", "Backspace", "Delete", "LCtrl", "RCtrl", "LShift", "RShift", "LAlt", "RAlt", "F1", "F2", "F3", "F4", "F5", "F6", "F7", "F8", "F9", "F10", "F11", "F12", "Comma", "Period", "Slash", "Backslash", "Semicolon", "Quote", "LeftBracket", "RightBracket", "Minus", "Equals", "Backquote", "Kp0", "Kp1", "Kp2", "Kp3", "Kp4", "Kp5", "Kp6", "Kp7", "Kp8", "Kp9", "KpDivide", "KpMultiply", "KpMinus", "KpPlus", "KpPeriod", "KpComma", "KpEnter", "KpEquals", "NumLockClear", "Home", "End", "PageUp", "PageDown", "Insert", "Pause", "CapsLock", "ScrollLock"];
const FONT_W: i32 = 9; const FONT_H: i32 = 19;
