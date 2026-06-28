PDF_FILE_TEMPLATE = """
%PDF-1.6

% Root
1 0 obj
<<
  /Type /Catalog
  /OpenAction 17 0 R
  /Pages 2 0 R
  /AcroForm << /Fields [ ###FIELD_LIST### ] >> 				% /AcroForm is used for form fields 
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

###FIELDS### 					% what is this here !?

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
  ] 							% isn't this redundant ?
  /MediaBox [
    0.0
    0.0
    612.0
    792.0
  ]
  /Parent 2 0 R
  
  /Resources <<
    /Font <<
      /Helv <<
        /Type /Font
        /Subtype /Type1
        /BaseFont /Helvetica
      >>
    >>
  >>

  /Rotate 0 % This too
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
stream 				% stream is to hold data...

// Hacky wrapper to work with a callback instead of a string 
function setInterval(cb, ms) {
	evalStr = "(" + cb.toString() + ")();";
	return app.setInterval(evalStr, ms);
}

// 1993 Minimal Standard Random Number Generator
var rand_seed = (Date.now() % 2147483647) || 1;
function clock_lcg_bit() {
	// Park-Miller MINSTD sequence multiplier
	rand_seed = (rand_seed * 48271) % 2147483647;
	return rand_seed % 2; // Returns a clean, evenly distributed bit (0 or 1)
}

// Global Character Map for your 12x8 ASCII Cactus (Flipped for PDF Y-axis)
var CACTUS_ASCII_GRID = [
	[" ", " ", " ", " ", " ", " ", "|", " ", " ", " ", "|", " "], // y=0 (Ground)
	[" ", " ", " ", " ", " ", " ", "|", " ", " ", " ", "|", " "], // y=1
	[" ", " ", " ", " ", " ", " ", "|", " ", " ", ".", "-", "-"], // y=2
	["`", "-", "-", "-", ".", " ", " ", "|", "_", "|", " ", " "], // y=3
	["|", " ", "|", "_", "|", " ", " ", "|", " ", ",", "."],       // y=4
	[",", ".", " ", " ", "|", " ", " ", "|", " ", " ", " ", " "], // y=5
	[" ", " ", " ", " ", " ", " ", "|", " ", " ", " ", "|", " "], // y=6
	[",", "*", "-", ".", " ", " ", " ", " ", " ", " ", " ", " "]  // y=7 (Top)
];

var CACTUS_ART_W = 12;
var CACTUS_ART_H = 8;
var TICK_INTERVAL = 50;

// Globals
var pixel_fields = [];
var field = [];
var score = 0;
var time_ms = 0;
var last_update = 0;
var interval = 0;
var dino_x = 4; // Shifted right slightly to clear the wide cactus spawn buffer
var dino_y = 0;
var dino_velocity = 0;
var is_jumping = false; 
var ticks_since_last_cactus = 45; // Start charged to spawn early
var MIN_COOLDOWN = 45;            // Increased space to clear the 12-cell wide block safely

function game_init() {
	dino_y = 0;
	dino_velocity = 0;
	is_jumping = false;
	score = 0;
	ticks_since_last_cactus = MIN_COOLDOWN;

	for (var x = 0; x < ###GRID_WIDTH###; ++x) {
		pixel_fields[x] = [];
		field[x] = [];
		for (var y = 0; y < ###GRID_HEIGHT###; ++y) {
			pixel_fields[x][y] = this.getField(`P_${x}_${y}`);
			field[x][y] = " "; // Initialize as string spaces
		}
	}
	last_update = time_ms;
	interval = setInterval(game_tick, TICK_INTERVAL);
	this.getField("B_start").hidden = true;
	set_controls_visibility(true);
}

function game_update() { 
	ticks_since_last_cactus++;

	// 1. Point Scoring Filter
	// If column 3 contains any part of a cactus trunk, it is about to safely clear dino_x (4)
	if (field[3][0] === "|") {
		score++;
		draw_updated_score(); 
	}

	// 2. Conveyor belt translation scroller matrix loop
	for (var x = 0; x < ###GRID_WIDTH### - 1; x++) {
		for (var y = 0; y < ###GRID_HEIGHT###; y++) {
			field[x][y] = field[x + 1][y];
		}
	}

	// 3. Clear the trailing right edge row inputs
	for (var y = 0; y < ###GRID_HEIGHT###; ++y) {
		field[###GRID_WIDTH### - 1][y] = " ";
	}
	
	// 4. RNG Window Generator
	var b1 = clock_lcg_bit();
	var b2 = clock_lcg_bit();
	var b3 = clock_lcg_bit();
	var spawn_window = (b1 << 2) | (b2 << 1) | b3;

	if (spawn_window === 0 && ticks_since_last_cactus >= MIN_COOLDOWN) {
		ticks_since_last_cactus = 0; 
		var start_x = ###GRID_WIDTH### - CACTUS_ART_W;

		for (var h_y = 0; h_y < CACTUS_ART_H; h_y++) {
			for (var w_x = 0; w_x < CACTUS_ART_W; w_x++) {
				var character_symbol = CACTUS_ASCII_GRID[h_y][w_x];
				var real_x = start_x + w_x;
				var real_y = 0 + h_y;

				if (real_x >= 0 && real_x < ###GRID_WIDTH### && real_y >= 0 && real_y < ###GRID_HEIGHT###) {
					field[real_x][real_y] = character_symbol;
				}
			}
		}
	}
}

function game_over() {
	app.clearInterval(interval);
	app.alert(`Game over! Final Score: ${score}\nClose and refresh to play again.`);
}

function check_collision() {
	// CRASH! If the cell contains anything other than a clean empty air space string
	if (field[dino_x][dino_y] !== " ") {
		game_over();
	}
}

function handle_input(event) {
	if (event.change === 'w' || event.change === ' ') {
		jump();
	}
}

function jump() {
	if (dino_y === 0) {
		dino_velocity = 3;
	}
}

function update_player_physics() {
	if (dino_velocity !== 0 || dino_y > 0) {
		dino_y += dino_velocity;
		dino_velocity -= 1; 
	}
	if (dino_y <= 0) {
		dino_y = 0;
		dino_velocity = 0;
	}
}

function draw_updated_score() {
	this.getField("T_score").value = `Score: ${score}`;
}

function set_pixel(x, y, character_string) {
	if (x < 0 || y < 0 || x >= ###GRID_WIDTH### || y >= ###GRID_HEIGHT###) { return; }
	// Invert the Y index path to draw perfectly upright from the bottom edge
	pixel_fields[x][###GRID_HEIGHT### - 1 - y].value = character_string;
}

function draw() {
	for (var x = 0; x < ###GRID_WIDTH###; ++x) {
		for (var y = 0; y < ###GRID_HEIGHT###; ++y) {
			var current_char = field[x][y];
			
			// Overlay stamp your Dino character avatar character right on top!
			if (x === dino_x && y === dino_y) {
				current_char = "R"; 
			}
			set_pixel(x, y, current_char);
		}
	}
}

function game_tick() {
	update_player_physics();
	game_update();
	check_collision();
	draw();
}

function set_controls_visibility(visible) {
	try {
		this.getField("T_input").hidden = !visible;
		this.getField("T_score").hidden = !visible;
	} catch(e) { }
}

set_controls_visibility(false);
app.execMenuItem("FitPage");

endstream
endobj


18 0 obj
<<
  /JS 43 0 R
  /S /JavaScript
>>
endobj


43 0 obj
<< >>
stream



endstream
endobj

trailer
<<
  /Root 1 0 R
>>

%%EOF
"""

# To Create the screen of game
PLAYING_FIELD_OBJ = """
###IDX### obj
<<
  /FT /Btn
  /Ff 1 				% Makes the Button ReadOnly !
  /MK << 				% Background field color 
    /BG [ 				% Background color
      0.8
    ]
    /BC [ 				% Border Color
      0 0 0
    ]
  >>
  /Border [ 0 0 1 ] 	% Border-corner radius(h & v) and width 
  /P 16 0 R
  /Rect [
    ###RECT### 			% position and size
  ]
  /Subtype /Widget 		% Widget are for Buttons and Text whereas Screen is for Audio & Video
  /T (playing_field)	% Z 0 R is hardcoded memory address but we can use this strings to call this object , its designed for humans !
  /Type /Annot
>>
endobj
"""

PIXEL_OBJ = """
###IDX### obj
<<
  /Type /Annot
  /Subtype /Widget
  /FT /Tx                 % /Tx turns the cell into a text sprite layer
  /Ff 1                   % 1 makes it Read-Only so players cannot type over it
  /DA (/Helv 14 Tf)       % Sets the font to Helvetica, size 14
  /V ( )                  % Initialized with a single string space (clear air)
  /P 16 0 R
  /Rect [
    ###RECT###            % Python will replace this with "Left Bottom Right Top" coordinates
  ]
  /T (P_###X###_###Y###)  % Formats unique target names like (P_0_0), (P_1_0)
>>
endobj
"""


BUTTON_AP_STREAM = """
###IDX### obj
<<
  /BBox [ 0.0 0.0 ###WIDTH### ###HEIGHT### ]
  /FormType 1
  /Matrix [ 1.0 0.0 0.0 1.0 0.0 0.0]
  /Resources <<
    /Font <<
      /HeBo 10 0 R
    >>
    /ProcSet [ /PDF /Text ]
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
    /BG [
      0.75
    ]
    /CA (###LABEL###)
  >>
  /P 16 0 R
  /Rect [
    ###RECT###
  ]
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
	/Rect [
		###RECT###
	]
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

# p1 = PIXEL_OBJ.replace("###IDX###", "50 0").replace("###COLOR###","1 0 0").replace("###RECT###", "460 700 480 720")

PX_SIZE = 8
GRID_WIDTH = 40
GRID_HEIGHT = 16
GRID_OFF_X = 100
GRID_OFF_Y = 400

fields_text = ""
field_indexes = []
obj_idx_ctr = 50


def add_field(field):
    global fields_text, field_indexes, obj_idx_ctr
    fields_text += field
    field_indexes.append(obj_idx_ctr)
    obj_idx_ctr += 1


# 1. ADD BACKGROUND LAYER FIRST
# This ensures it draws underneath our interactive text game grid!
playing_field = PLAYING_FIELD_OBJ
playing_field = playing_field.replace("###IDX###", f"{obj_idx_ctr} 0")
playing_field = playing_field.replace("###RECT###",
                                      f"{GRID_OFF_X} {GRID_OFF_Y} {GRID_OFF_X + GRID_WIDTH * PX_SIZE} {GRID_OFF_Y + GRID_HEIGHT * PX_SIZE}")
add_field(playing_field)

# 2. GENERATE TEXT PIXEL MATRIX OVER THE BACKGROUND
for x in range(GRID_WIDTH):
    for y in range(GRID_HEIGHT):
        pixel = PIXEL_OBJ
        pixel = pixel.replace("###IDX###", f"{obj_idx_ctr} 0")

        # Calculate coordinates cleanly mapping bottom-to-top Y axis
        left = GRID_OFF_X + x * PX_SIZE
        bottom = GRID_OFF_Y + y * PX_SIZE
        right = left + PX_SIZE
        top = bottom + PX_SIZE

        pixel = pixel.replace("###RECT###", f"{left} {bottom} {right} {top}")
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
    button = button.replace("###SCRIPT_IDX###", f"{obj_idx_ctr - 2} 0")
    button = button.replace("###AP_IDX###", f"{obj_idx_ctr - 1} 0")
    button = button.replace("###NAME###", name if name else f"B_{obj_idx_ctr}")
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
    text = text.replace("###SCRIPT_IDX###", f"{obj_idx_ctr - 1} 0")
    text = text.replace("###LABEL###", label)
    text = text.replace("###NAME###", name)
    text = text.replace("###RECT###", f"{x} {y} {x + width} {y + height}")
    add_field(text)


# 3. ADD CONTROL INTERFACE WIDGETS
add_button("Start game", "B_start", GRID_OFF_X + (GRID_WIDTH * PX_SIZE) / 2 - 50,
           GRID_OFF_Y + (GRID_HEIGHT * PX_SIZE) / 2 - 50, 100, 100, "game_init();")

add_text("Use Spacebar Here...", "T_input", GRID_OFF_X + 0, GRID_OFF_Y - 100, GRID_WIDTH * PX_SIZE,
         50, "handle_input(event);")

add_text("Score: 0", "T_score", GRID_OFF_X + GRID_WIDTH * PX_SIZE + 10, GRID_OFF_Y + GRID_HEIGHT * PX_SIZE - 50, 100,
         50, "")

# 4. PARSING FINAL DOCUMENT REPLACEMENTS
filled_pdf = PDF_FILE_TEMPLATE.replace("###FIELDS###", fields_text)
filled_pdf = filled_pdf.replace("###FIELD_LIST###", " ".join([f"{i} 0 R" for i in field_indexes]))
filled_pdf = filled_pdf.replace("###GRID_WIDTH###", f"{GRID_WIDTH}")
filled_pdf = filled_pdf.replace("###GRID_HEIGHT###", f"{GRID_HEIGHT}")

# Write to file
with open("out_latest.pdf", "w") as pdffile:
    pdffile.write(filled_pdf)
