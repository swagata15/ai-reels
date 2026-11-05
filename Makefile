# Usage: make reel R=neon_orb   |   make draft R=kinetic_title   |   make post R=neon_orb MUSIC=music/x.mp3
BLENDER ?= blender
PYTHON  ?= python3
R       ?= neon_orb
SPEC    := $(firstword $(wildcard reels/$(R).json reels/examples/$(R).json))
NAME    := $(shell $(PYTHON) -c "import json;print(json.load(open('$(SPEC)'))['name'])")
MUSIC   ?=
POSTFLAGS ?= --glow --grain

.PHONY: reel draft render post clean

reel: render post

render:
	$(BLENDER) -b -P scripts/render_reel.py -- $(SPEC)

draft:
	$(BLENDER) -b -P scripts/render_reel.py -- $(SPEC) --draft --frames 1-60
	$(PYTHON) scripts/postprocess.py output/$(NAME) $(POSTFLAGS)

post:
	$(PYTHON) scripts/postprocess.py output/$(NAME) $(POSTFLAGS) $(if $(MUSIC),--music $(MUSIC),)

clean:
	rm -rf output
