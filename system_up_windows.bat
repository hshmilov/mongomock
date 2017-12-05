@echo off
echo %1%
IF "%1%" == "up" (
    echo "Starting system up!"
    cd plugins/axonius-libs
	docker build -t axonius/axonius-libs . 
	cd ../..
    cd devops/systemization/database
	docker-compose up -d
	cd ../../..
    cd devops/systemization/logging
	docker-compose up -d
	cd ../../..
    cd plugins/core
	docker-compose up -d
	cd ../..
    cd plugins/aggregator-plugin
	docker-compose up -d
	cd ../..
)

IF "%1%" == "down" (
    echo "Bringing system down!"
    cd devops/systemization/database
	docker-compose down
	cd ../../..
    cd devops/systemization/logging
	docker-compose down
	cd ../../..
    cd plugins/core
	docker-compose down
	cd ../..
    cd plugins/aggregator-plugin
	docker-compose down
	cd ../..
)