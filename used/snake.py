PDF_FILE_TEMPLATE = """
%PDF-1.6

% Root
1 0 obj
<<
  /AcroForm <<
    /Fields [ ###FIELD_LIST### ]
  >>
  /Pages 2 0 R
  /OpenAction 17 0 R
  /Type /Catalog
>>
endobj

2 0 obj
<<
  /Count 1
  /Kids [
    16 0 R
  ]
  /Type /Pages
>>

%% Annots Page 1 (also used as overall fields list)
21 0 obj
[
  ###FIELD_LIST###
]
endobj

###FIELDS###

%% Page 1
16 0 obj
<<
  /Annots 21 0 R
  /Contents 3 0 R
  /CropBox [
    0.0
    0.0
    612.0
    792.0
  ]
  /MediaBox [
    0.0
    0.0
    612.0
    792.0
  ]
  /Parent 2 0 R
  /Resources <<
  >>
  /Rotate 0
  /Type /Page
>>
endobj

3 0 obj
<< >>
stream
endstream
endobj

17 0 obj
<<
  /JS 42 0 R
  /S /JavaScript
>>
endobj

42 0 obj
<< >>
stream

// Hacky wrapper to work with a callback instead of a string 
function setInterval(cb, ms) {
    evalStr = "(" + cb.toString() + ")();";
    return app.setInterval(evalStr, ms);
}

// Simple random number generator
var rand_seed = Date.now() % 2147483647;
function rand() {
    return rand_seed = rand_seed * 16807 % 2147483647;
}

// Game constants
var TICK_INTERVAL = 50;
var GAME_STEP_TIME = 500; // Slower speed: 500ms per move

// Globals
var pixel_fields = [];
var field = []; // 0 = empty, 1 = snake, 2 = food
var snake = [{x: 10, y: 15}]; // Starting position adjusted for larger grid
var food = {x: 15, y: 20}; // Initial food position
var direction = {x: 1, y: 0}; // Start moving right
var score = 0;
var time_ms = 0;
var last_update = 0;
var interval = 0;

function spawn_food() {
    food.x = Math.floor(rand() % ###GRID_WIDTH###);
    food.y = Math.floor(rand() % ###GRID_HEIGHT###);
    // Ensure food doesn't spawn on snake
    for (var i = 0; i < snake.length; i++) {
        if (snake[i].x === food.x && snake[i].y === food.y) {
            spawn_food();
            return;
        }
    }
}

function set_controls_visibility(state) {
    this.getField("T_input").hidden = !state;
    this.getField("B_left").hidden = !state;
    this.getField("B_right").hidden = !state;
    this.getField("B_down").hidden = !state;
    this.getField("B_up").hidden = !state;
}

function game_init() {
    snake = [{x: 10, y: 15}];
    direction = {x: 1, y: 0};
    score = 0;
    spawn_food();

    // Initialize grid
    for (var x = 0; x < ###GRID_WIDTH###; x++) {
        pixel_fields[x] = [];
        field[x] = [];
        for (var y = 0; y < ###GRID_HEIGHT###; y++) {
            pixel_fields[x][y] = this.getField(`P_${x}_${y}`);
            field[x][y] = 0;
        }
    }

    last_update = time_ms;
    interval = setInterval(game_tick, TICK_INTERVAL);
    this.getField("B_start").hidden = true;
    set_controls_visibility(true);
    draw_updated_score();
}

function game_update() {
    if (time_ms - last_update >= GAME_STEP_TIME) {
        move_snake();
        last_update = time_ms;
    }
}

function game_over() {
    app.clearInterval(interval);
    app.alert(`Game Over! Score: ${score}\\nRefresh to restart.`);
}

function move_snake() {
    var head = {x: snake[0].x + direction.x, y: snake[0].y + direction.y};

    // Check wall collision
    if (head.x < 0 || head.x >= ###GRID_WIDTH### || head.y < 0 || head.y >= ###GRID_HEIGHT###) {
        game_over();
        return;
    }

    // Check self collision
    for (var i = 0; i < snake.length; i++) {
        if (head.x === snake[i].x && head.y === snake[i].y) {
            game_over();
            return;
        }
    }

    snake.unshift(head); // Add new head

    // Check if food is eaten
    if (head.x === food.x && head.y === food.y) {
        score += 10;
        spawn_food();
        draw_updated_score();
    } else {
        snake.pop(); // Remove tail if no food eaten
    }
}

function handle_input(event) {
    switch (event.change) {
        case 'w': if (direction.y !== 1) direction = {x: 0, y: -1}; break; // Up
        case 's': if (direction.y !== -1) direction = {x: 0, y: 1}; break; // Down
        case 'a': if (direction.x !== 1) direction = {x: -1, y: 0}; break; // Left
        case 'd': if (direction.x !== -1) direction = {x: 1, y: 0}; break; // Right
    }
}

function move_left() { if (direction.x !== 1) direction = {x: -1, y: 0}; }
function move_right() { if (direction.x !== -1) direction = {x: 1, y: 0}; }
function move_down() { if (direction.y !== -1) direction = {x: 0, y: 1}; }
function move_up() { if (direction.y !== 1) direction = {x: 0, y: -1}; }

function draw_updated_score() {
    this.getField("T_score").value = `Score: ${score}`;
}

function set_pixel(x, y, state) {
    if (x < 0 || y < 0 || x >= ###GRID_WIDTH### || y >= ###GRID_HEIGHT###) return;
    pixel_fields[x][###GRID_HEIGHT### - 1 - y].hidden = !state;
}

function draw() {
    // Clear field
    for (var x = 0; x < ###GRID_WIDTH###; x++) {
        for (var y = 0; y < ###GRID_HEIGHT###; y++) {
            set_pixel(x, y, 0);
        }
    }
    // Draw snake
    for (var i = 0; i < snake.length; i++) {
        set_pixel(snake[i].x, snake[i].y, 1);
    }
    // Draw food
    set_pixel(food.x, food.y, 1);
}

function game_tick() {
    time_ms += TICK_INTERVAL;
    game_update();
    draw();
}

// Hide controls initially
set_controls_visibility(false);
app.execMenuItem("FitPage");

endstream
endobj

trailer
<<
  /Root 1 0 R
>>

%%EOF
"""

PLAYING_FIELD_OBJ = """
###IDX### obj
<<
  /FT /Btn
  /Ff 1
  /MK <<
    /BG [0.8]
    /BC [0 0 0]
  >>
  /Border [0 0 1]
  /P 16 0 R
  /Rect [###RECT###]
  /Subtype /Widget
  /T (playing_field)
  /Type /Annot
>>
endobj
"""

PIXEL_OBJ = """
###IDX### obj
<<
  /FT /Btn
  /Ff 1
  /MK <<
    /BG [###COLOR###]
    /BC [0.5 0.5 0.5]
  >>
  /Border [0 0 1]
  /P 16 0 R
  /Rect [###RECT###]
  /Subtype /Widget
  /T (P_###X###_###Y###)
  /Type /Annot
>>
endobj
"""

BUTTON_AP_STREAM = """
###IDX### obj
<<
  /BBox [0.0 0.0 ###WIDTH### ###HEIGHT###]
  /FormType 1
  /Matrix [1.0 0.0 0.0 1.0 0.0 0.0]
  /Resources <<
    /Font <<
      /HeBo 10 0 R
    >>
    /ProcSet [/PDF /Text]
  >>
  /Subtype /Form
  /Type /XObject
>>
stream
q
0.75 g
0 0 ###WIDTH### ###HEIGHT### re
f
Q
q
1 1 ###WIDTH### ###HEIGHT### re
W
n
BT
/HeBo 12 Tf
0 g
10 8 Td
(###TEXT###) Tj
ET
Q
endstream
endobj
"""

BUTTON_OBJ = """
###IDX### obj
<<
  /A <<
    /JS ###SCRIPT_IDX### R
    /S /JavaScript
  >>
  /AP <<
    /N ###AP_IDX### R
  >>
  /F 4
  /FT /Btn
  /Ff 65536
  /MK <<
    /BG [0.75]
    /CA (###LABEL###)
  >>
  /P 16 0 R
  /Rect [###RECT###]
  /Subtype /Widget
  /T (###NAME###)
  /Type /Annot
>>
endobj
"""

TEXT_OBJ = """
###IDX### obj
<<
  /AA <<
    /K <<
      /JS ###SCRIPT_IDX### R
      /S /JavaScript
    >>
  >>
  /F 4
  /FT /Tx
  /MK <<
  >>
  /MaxLen 0
  /P 16 0 R
  /Rect [###RECT###]
  /Subtype /Widget
  /T (###NAME###)
  /V (###LABEL###)
  /Type /Annot
>>
endobj
"""

STREAM_OBJ = """
###IDX### obj
<< >>
stream
###CONTENT###
endstream
endobj
"""

# Grid settings
PX_SIZE = 20
GRID_WIDTH = 10  # Increased from 10
GRID_HEIGHT = 20  # Increased from 20
GRID_OFF_X = 200  # Adjusted to fit larger grid on page
GRID_OFF_Y = 350  # Adjusted to fit larger grid on page

fields_text = ""
field_indexes = []
obj_idx_ctr = 50

def add_field(field):
    global fields_text, field_indexes, obj_idx_ctr
    fields_text += field
    field_indexes.append(obj_idx_ctr)
    obj_idx_ctr += 1

# Playing field outline
playing_field = PLAYING_FIELD_OBJ
playing_field = playing_field.replace("###IDX###", f"{obj_idx_ctr} 0")
playing_field = playing_field.replace("###RECT###", f"{GRID_OFF_X} {GRID_OFF_Y} {GRID_OFF_X+GRID_WIDTH*PX_SIZE} {GRID_OFF_Y+GRID_HEIGHT*PX_SIZE}")
add_field(playing_field)

# Create pixel grid
for x in range(GRID_WIDTH):
    for y in range(GRID_HEIGHT):
        pixel = PIXEL_OBJ
        pixel = pixel.replace("###IDX###", f"{obj_idx_ctr} 0")
        pixel = pixel.replace("###COLOR###", "0 1 0")  # Green for snake/food
        pixel = pixel.replace("###RECT###", f"{GRID_OFF_X+x*PX_SIZE} {GRID_OFF_Y+y*PX_SIZE} {GRID_OFF_X+x*PX_SIZE+PX_SIZE} {GRID_OFF_Y+y*PX_SIZE+PX_SIZE}")
        pixel = pixel.replace("###X###", f"{x}")
        pixel = pixel.replace("###Y###", f"{y}")
        add_field(pixel)

def add_button(label, name, x, y, width, height, js):
    global obj_idx_ctr
    script = STREAM_OBJ
    script = script.replace("###IDX###", f"{obj_idx_ctr} 0")
    script = script.replace("###CONTENT###", js)
    add_field(script)

    ap_stream = BUTTON_AP_STREAM
    ap_stream = ap_stream.replace("###IDX###", f"{obj_idx_ctr} 0")
    ap_stream = ap_stream.replace("###TEXT###", label)
    ap_stream = ap_stream.replace("###WIDTH###", f"{width}")
    ap_stream = ap_stream.replace("###HEIGHT###", f"{height}")
    add_field(ap_stream)

    button = BUTTON_OBJ
    button = button.replace("###IDX###", f"{obj_idx_ctr} 0")
    button = button.replace("###SCRIPT_IDX###", f"{obj_idx_ctr-2} 0")
    button = button.replace("###AP_IDX###", f"{obj_idx_ctr-1} 0")
    button = button.replace("###NAME###", name)
    button = button.replace("###RECT###", f"{x} {y} {x + width} {y + height}")
    add_field(button)

def add_text(label, name, x, y, width, height, js):
    global obj_idx_ctr
    script = STREAM_OBJ
    script = script.replace("###IDX###", f"{obj_idx_ctr} 0")
    script = script.replace("###CONTENT###", js)
    add_field(script)

    text = TEXT_OBJ
    text = text.replace("###IDX###", f"{obj_idx_ctr} 0")
    text = text.replace("###SCRIPT_IDX###", f"{obj_idx_ctr-1} 0")
    text = text.replace("###LABEL###", label)
    text = text.replace("###NAME###", name)
    text = text.replace("###RECT###", f"{x} {y} {x + width} {y + height}")
    add_field(text)

# Add four movement buttons in a cross layout
add_button("<", "B_left", GRID_OFF_X + GRID_WIDTH*PX_SIZE + 20, GRID_OFF_Y + GRID_HEIGHT*PX_SIZE/2 - 25, 50, 50, "move_left();")
add_button(">", "B_right", GRID_OFF_X + GRID_WIDTH*PX_SIZE + 80, GRID_OFF_Y + GRID_HEIGHT*PX_SIZE/2 - 25, 50, 50, "move_right();")
add_button("/\\", "B_up", GRID_OFF_X + GRID_WIDTH*PX_SIZE + 50, GRID_OFF_Y + GRID_HEIGHT*PX_SIZE/2 + 35, 50, 50, "move_up();")
add_button("\\/", "B_down", GRID_OFF_X + GRID_WIDTH*PX_SIZE + 50, GRID_OFF_Y + GRID_HEIGHT*PX_SIZE/2 - 85, 50, 50, "move_down();")
add_button("Start", "B_start", GRID_OFF_X + (GRID_WIDTH*PX_SIZE)/2 - 50, GRID_OFF_Y + (GRID_HEIGHT*PX_SIZE)/2 - 50, 100, 100, "game_init();")

add_text("Type WASD for controls", "T_input", GRID_OFF_X, GRID_OFF_Y - 50, GRID_WIDTH*PX_SIZE, 50, "handle_input(event);")
add_text("Score: 0", "T_score", GRID_OFF_X + GRID_WIDTH*PX_SIZE + 20, GRID_OFF_Y + GRID_HEIGHT*PX_SIZE + 20, 100, 50, "")

# Finalize PDF
filled_pdf = PDF_FILE_TEMPLATE.replace("###FIELDS###", fields_text)
filled_pdf = filled_pdf.replace("###FIELD_LIST###", " ".join([f"{i} 0 R" for i in field_indexes]))
filled_pdf = filled_pdf.replace("###GRID_WIDTH###", f"{GRID_WIDTH}")
filled_pdf = filled_pdf.replace("###GRID_HEIGHT###", f"{GRID_HEIGHT}")

with open("snake_game.pdf", "w") as pdffile:
    pdffile.write(filled_pdf)