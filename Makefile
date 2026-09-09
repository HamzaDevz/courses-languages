.PHONY: build pdf serve clean install

install:            ## Installe la seule dépendance (PyYAML)
	python3 -m pip install -r requirements.txt

build:              ## Génère site/, print/ et exports/ depuis content/
	python3 scripts/build.py

pdf: build          ## Convertit les fiches en PDF (nécessite Chrome/Chromium)
	python3 scripts/pdf.py

serve: build        ## Ouvre le site en local sur http://localhost:8000
	@echo "→ http://localhost:8000"
	@python3 -m http.server 8000 --directory site

clean:              ## Supprime tout ce qui est généré
	rm -rf site print pdf exports
