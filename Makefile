.PHONY: build audio pdf serve clean install install-audio

install:            ## Installe la seule dépendance (PyYAML)
	python3 -m pip install -r requirements.txt

build:              ## Génère site/, print/ et exports/ depuis content/
	python3 scripts/build.py

install-audio:      ## Installe edge-tts, nécessaire seulement pour « make audio »
	python3 -m pip install -r requirements-audio.txt

audio:              ## Enregistre chaque mot et chaque réplique en vraie voix portugaise
	python3 scripts/audio.py
	python3 scripts/build.py

pdf: build          ## Convertit les fiches en PDF (nécessite Chrome/Chromium)
	python3 scripts/pdf.py

serve: build        ## Ouvre le site en local sur http://localhost:8000
	@echo "→ http://localhost:8000"
	@python3 -m http.server 8000 --directory site

clean:              ## Supprime tout ce qui est généré
	rm -rf site print pdf exports
