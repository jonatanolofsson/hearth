cloc:
	cloc --exclude-dir=__pycache__ hearth js ../hearthsetup www/index.html

bash:
	docker-compose exec -w /hearth hearth /bin/bash

build:
	yarn run build

upgrade:
	yarn upgrade
