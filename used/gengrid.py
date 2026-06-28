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
  /Resources <<>> 				% why he wrote this ?
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

// https://gist.github.com/blixt/f17b47c62508be59987b
var rand_seed = Date.now() % 2147483647;
function rand() {
	return rand_seed = rand_seed * 16807 % 2147483647;
}

function clock_127_bit() {
	// Read the specific taps natively using quick masks
	var bit0 = rand_seed & 1;
	var bit1 = (rand_seed & 2) >> 1;
	var bit2 = (rand_seed & 4) >> 2;
	var bit7 = (rand_seed & 128) >> 7;
	
	var new_bit = bit0 ^ bit1 ^ bit2 ^ bit7;
	
	// Advance the standard 31-bit generator math sequence
	rand_seed = (rand_seed * 16807) % 2147483647;
	if (rand_seed === 0) { rand_seed = 1; }
	
	return bit0;
}

// and j == 0 for X coord, j == 1 for Y coord
var obstacle_data = [
	
	// Single Cactus
	[0,0,  0,1,  -1,1,  1,1,  0,2],

	// Double Cactus
	[0,0,  2,0,  0,1,  1,1,  2,1,  -1,1,  3,1,  0,2,  2,2]
];

var TICK_INTERVAL = 50;  	// frames per-second
var GAME_STEP_TIME = 50; 	// cactuses should move forward on every frame so...

// Globals
var pixel_fields = [];
var field = [];
var score = 0;
var time_ms = 0;
var last_update = 0;
var interval = 0;
var dino_x = 2;
var dino_y = 0;
var dino_velocity = 0;		// to calculate fallback and jumping i.e gravity
var is_jumping = false; 	// to avoid double jumping 
var ticks_since_last_cactus = 35; // to provide breathing room to the players 
var MIN_COOLDOWN = 35;


function game_init() {
	
	// Gather references to pixel field objects
	// and initialize game state
	for (var x = 0; x < ###GRID_WIDTH###; ++x) {
		pixel_fields[x] = [];
		field[x] = [];
		for (var y = 0; y < ###GRID_HEIGHT###; ++y) {
			pixel_fields[x][y] = this.getField(`P_${x}_${y}`);
			field[x][y] = 0;
		}
	}

	last_update = time_ms;
	score = 0;

	// Start timer
	interval = setInterval(game_tick, TICK_INTERVAL);

	// Hide start button
	this.getField("B_start").hidden = true;

	// Show input box and controls
	set_controls_visibility(true);
}

function game_update() { 
	ticks_since_last_cactus++;
	
	// Shift the entire matrix left by 1 column
	for (var x = 0; x < ###GRID_WIDTH### - 1; x++) {
		for (var y = 0; y < ###GRID_HEIGHT###; y++) {
			field[x][y] = field[x + 1][y];
		}
	}

	// Clear out the far-right column
	for (var y = 0; y < ###GRID_HEIGHT###; ++y) {
		field[###GRID_WIDTH### - 1][y] = 0;
	}
	// cactus reached column 1 so give the damn point !
	if (field[1][0] === 1) {
		score++;
		draw_updated_score(); 
	}
	
	var b1 = clock_127_bit();
	var b2 = clock_127_bit();
	var b3 = clock_127_bit();
	var spawn_window = (b1 << 2) | (b2 << 1) | b3;

	if (spawn_window === 0 && ticks_since_last_cactus >= MIN_COOLDOWN) {
		ticks_since_last_cactus = 0; // Trigger the cooldown lock

		// Roll a 4th bit right now to choose obstacle variant type
		var type_bit = clock_127_bit();
		var obstacle_idx = (type_bit === 1) ? 1 : 0; // 0 = Single, 1 = Double

		var shape = obstacle_data[obstacle_idx];
		var blocks_count = shape.length / 2;

		// Map relative brick coordinates onto the far-right side of the canvas
		for (var p = 0; p < blocks_count; p++) {
			var x_off = shape[p * 2 + 0];
			var y_off = shape[p * 2 + 1];

			var real_x = (###GRID_WIDTH### - 1) + x_off;
			var real_y = 0 + y_off;

			// Write into array bounds safely
			if (real_x >= 0 && real_x < ###GRID_WIDTH### && real_y >= 0 && real_y < ###GRID_HEIGHT###) {
				field[real_x][real_y] = 1;
			}
		}
	}
}

function game_over() {
	app.clearInterval(interval);
	app.alert(`Game over! Score: ${score}\nRefresh to restart.`);
}


function check_collision() {
	if (field[dino_x][dino_y] === 1){
		game_over();
		return;
	}
}

function handle_input(event) {
	if (event.change === 'w' || event.change === ' ') {
		jump();
	}
}

function jump() {
	if (dino_y === 0){
		dino_velocity = 3;
	}
}

function update_player_physics() {
	// If we have vertical momentum (jumping or falling), update the position
	if (dino_velocity !== 0 || dino_y > 0) {
		dino_y += dino_velocity;
		dino_velocity -= 1; // Pull down by gravity
	}
	
	// If we touch or pass the ground line, land safely
	if (dino_y <= 0) {
		dino_y = 0;
		dino_velocity = 0;
	}
}


function draw_updated_score() {
	this.getField("T_score").value = `Score: ${score}`;
}

function set_pixel(x, y, state) {
	if (x < 0 || y < 0 || x >= ###GRID_WIDTH### || y >= ###GRID_HEIGHT###) {
		return;
	}
	pixel_fields[x][###GRID_HEIGHT### - 1 - y].hidden = !state;
}

function draw_field() {
	for (var x = 0; x < ###GRID_WIDTH###; ++x) {
		for (var y = 0; y < ###GRID_HEIGHT###; ++y) {
			set_pixel(x, y, field[x][y]);
		}
	}
}

function draw() {
	draw_field();
	set_pixel(dino_x, dino_y, 1);
}

function game_tick() {
	update_player_physics();
	check_collision();
	game_update();
	draw();
}

// Hide controls to start with
set_controls_visibility(false);

// Zoom to fit (on FF)
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
  /FT /Btn
  /Ff 1
  /MK <<
    /BG [
      ###COLOR###
    ]
    /BC [
      0.5 0.5 0.5
    ]
  >>
  /Border [ 0 0 1 ]
  /P 16 0 R
  /Rect [
    ###RECT###
  ]
  /Subtype /Widget
  /T (P_###X###_###Y###)
  /Type /Annot
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
# for rectangle
GRID_WIDTH = 40
GRID_HEIGHT = 12
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


# Playing field outline
playing_field = PLAYING_FIELD_OBJ
playing_field = playing_field.replace("###IDX###", f"{obj_idx_ctr} 0")
playing_field = playing_field.replace("###RECT###", f"{GRID_OFF_X} {GRID_OFF_Y} {GRID_OFF_X+GRID_WIDTH*PX_SIZE} {GRID_OFF_Y+GRID_HEIGHT*PX_SIZE}")
add_field(playing_field)

for x in range(GRID_WIDTH):
	for y in range(GRID_HEIGHT):
		# Build object
		pixel = PIXEL_OBJ
		pixel = pixel.replace("###IDX###", f"{obj_idx_ctr} 0")
		c = [0, 0, 0]
		pixel = pixel.replace("###COLOR###", f"{c[0]} {c[1]} {c[2]}")
		pixel = pixel.replace("###RECT###", f"{GRID_OFF_X+x*PX_SIZE} {GRID_OFF_Y+y*PX_SIZE} {GRID_OFF_X+x*PX_SIZE+PX_SIZE} {GRID_OFF_Y+y*PX_SIZE+PX_SIZE}")
		pixel = pixel.replace("###X###", f"{x}")
		pixel = pixel.replace("###Y###", f"{y}")

		add_field(pixel)

def add_button(label, name, x, y, width, height, js):
	script = STREAM_OBJ;
	script = script.replace("###IDX###", f"{obj_idx_ctr} 0")
	script = script.replace("###CONTENT###", js)
	add_field(script)

	ap_stream = BUTTON_AP_STREAM;
	ap_stream = ap_stream.replace("###IDX###", f"{obj_idx_ctr} 0")
	ap_stream = ap_stream.replace("###TEXT###", label)
	ap_stream = ap_stream.replace("###WIDTH###", f"{width}")
	ap_stream = ap_stream.replace("###HEIGHT###", f"{height}")
	add_field(ap_stream)

	button = BUTTON_OBJ;
	button = button.replace("###IDX###", f"{obj_idx_ctr} 0")
	button = button.replace("###SCRIPT_IDX###", f"{obj_idx_ctr-2} 0")
	button = button.replace("###AP_IDX###", f"{obj_idx_ctr-1} 0")
	#button = button.replace("###LABEL###", label)
	button = button.replace("###NAME###", name if name else f"B_{obj_idx_ctr}")
	button = button.replace("###RECT###", f"{x} {y} {x + width} {y + height}")
	add_field(button)

def add_text(label, name, x, y, width, height, js):
	script = STREAM_OBJ;
	script = script.replace("###IDX###", f"{obj_idx_ctr} 0")
	script = script.replace("###CONTENT###", js)
	add_field(script)

	text = TEXT_OBJ;
	text = text.replace("###IDX###", f"{obj_idx_ctr} 0")
	text = text.replace("###SCRIPT_IDX###", f"{obj_idx_ctr-1} 0")
	text = text.replace("###LABEL###", label)
	text = text.replace("###NAME###", name)
	text = text.replace("###RECT###", f"{x} {y} {x + width} {y + height}")
	add_field(text)


add_button("Start game", "B_start", GRID_OFF_X + (GRID_WIDTH*PX_SIZE)/2-50, GRID_OFF_Y + (GRID_HEIGHT*PX_SIZE)/2-50, 100, 100, "game_init();")
add_text("Type here for keyboard controls (WASD)", "T_input", GRID_OFF_X + 0, GRID_OFF_Y - 200, GRID_WIDTH*PX_SIZE, 50, "handle_input(event);")

add_text("Score: 0", "T_score", GRID_OFF_X + GRID_WIDTH*PX_SIZE+10, GRID_OFF_Y + GRID_HEIGHT*PX_SIZE-50, 100, 50, "")

filled_pdf = PDF_FILE_TEMPLATE.replace("###FIELDS###", fields_text)
filled_pdf = filled_pdf.replace("###FIELD_LIST###", " ".join([f"{i} 0 R" for i in field_indexes]))
filled_pdf = filled_pdf.replace("###GRID_WIDTH###", f"{GRID_WIDTH}")
filled_pdf = filled_pdf.replace("###GRID_HEIGHT###", f"{GRID_HEIGHT}")

pdffile = open("out_new.pdf","w")
pdffile.write(filled_pdf)
pdffile.close()
