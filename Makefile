# Usage: make reel R=neon_orb   |   make draft R=kinetic_title   |   make post R=neon_orb MUSIC=music/x.mp3
BLENDER ?= blender
PYTHON  ?= python3
R       ?= neon_orb
NAME    := $(shell $(PYTHON) -c "import json;print(json.load(open('reels/examples/$(R).json'))['name'])")
MUSIC   ?=
POSTFLAGS ?= --glow --grain

.PHONY: reel draft render post clean

reel: render post

render:
	$(BLENDER) -b -P scripts/render_reel.py -- reels/examples/$(R).json

draft:
	$(BLENDER) -b -P scripts/render_reel.py -- reels/examples/$(R).json --draft --frames 1-60
	$(PYTHON) scripts/postprocess.py output/$(NAME) $(POSTFLAGS)

post:
	$(PYTHON) scripts/postprocess.py output/$(NAME) $(POSTFLAGS) $(if $(MUSIC),--music $(MUSIC),)

clean:
	rm -rf output
