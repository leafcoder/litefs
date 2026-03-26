@echo off
setlocal enabledelayedexpansion

if "%1"=="" goto help
if "%1"=="help" goto help
if "%1"=="install" goto install
if "%1"=="dev-install" goto dev-install
if "%1"=="dev-uninstall" goto dev-uninstall
if "%1"=="clean" goto clean
if "%1"=="build" goto build
if "%1"=="wheel" goto wheel
if "%1"=="test" goto test
if "%1"=="test-unit" goto test-unit
if "%1"=="test-cov" goto test-cov
if "%1"=="serve" goto serve
if "%1"=="dev-serve" goto dev-serve
if "%1"=="wsgi-gunicorn" goto wsgi-gunicorn
if "%1"=="wsgi-uwsgi" goto wsgi-uwsgi
if "%1"=="wsgi-waitress" goto wsgi-waitress
if "%1"=="format" goto format
if "%1"=="lint" goto lint
if "%1"=="type-check" goto type-check
if "%1"=="check-all" goto check-all
goto :eof

:help
echo Litefs Development Commands
echo.
echo Installation:
echo   make.bat install          - Install package to current environment
echo   make.bat dev-install       - Install in development mode (editable)
echo   make.bat dev-uninstall     - Uninstall development installation
echo.
echo Development:
echo   make.bat format            - Format code (black + isort)
echo   make.bat lint              - Code linting (ruff)
echo   make.bat type-check        - Type checking (mypy)
echo   make.bat check-all         - Run all checks (format + lint + type-check)
echo.
echo Testing:
echo   make.bat test              - Run all tests
echo   make.bat test-unit        - Run unit tests
echo   make.bat test-cov         - Run tests with coverage report
echo.
echo Server:
echo   make.bat serve             - Start dev server (default port 9090)
echo   make.bat dev-serve         - Start dev server (debug mode)
echo   make.bat wsgi-gunicorn     - Start WSGI server with Gunicorn
echo   make.bat wsgi-uwsgi        - Start WSGI server with uWSGI
echo   make.bat wsgi-waitress    - Start WSGI server with Waitress
echo.
echo Build:
echo   make.bat build             - Build source distribution
echo   make.bat wheel             - Build wheel package
echo   make.bat clean             - Clean build files
echo.
echo Release:
echo   make.bat upload-test       - Upload to test PyPI
echo   make.bat upload            - Upload to PyPI
goto :eof

:install
python setup.py install
goto :eof

:dev-install
python -m pip install -e .
goto :eof

:dev-uninstall
python -m pip uninstall -y litefs
goto :eof

:clean
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist
if exist __pycache__ rmdir /s /q __pycache__
if exist src\__pycache__ rmdir /s /q src\__pycache__
if exist tests\__pycache__ rmdir /s /q tests\__pycache__
if exist .coverage del /q .coverage
if exist htmlcov rmdir /s /q htmlcov
if exist .mypy_cache rmdir /s /q .mypy_cache
if exist .ruff_cache rmdir /s /q .ruff_cache
if exist .pytest_cache rmdir /s /q .pytest_cache
goto :eof

:build
python setup.py build sdist
goto :eof

:wheel
python setup.py bdist_wheel
goto :eof

:test
echo Running all tests...
set PYTHONPATH=src
python -m pytest tests/ -v
goto :eof

:test-unit
echo Running unit tests...
set PYTHONPATH=src
python -m pytest tests/unit/ -v
goto :eof

:test-cov
echo Running tests with coverage...
set PYTHONPATH=src
python -m pytest tests/ --cov=src --cov-report=html --cov-report=term
echo Coverage report generated: htmlcov\index.html
goto :eof

:serve
echo Starting development server...
echo Access: http://localhost:9090/
echo Press Ctrl+C to stop
set PYTHONPATH=src
python -m litefs --host localhost --port 9090 --webroot examples\basic\site
goto :eof

:dev-serve
echo Starting development server (debug mode)...
echo Access: http://localhost:9090/
echo Press Ctrl+C to stop
set PYTHONPATH=src
python -m litefs --host localhost --port 9090 --webroot examples\basic\site --debug
goto :eof

:wsgi-gunicorn
echo Starting WSGI server with Gunicorn...
echo Access: http://localhost:9090/
echo Press Ctrl+C to stop
echo.
echo Install Gunicorn: pip install gunicorn
gunicorn -w 4 -b localhost:9090 --access-logfile - --error-logfile - --log-level info examples.wsgi.wsgi_example:application
goto :eof

:wsgi-uwsgi
echo Starting WSGI server with uWSGI...
echo Access: http://localhost:9090/
echo Press Ctrl+C to stop
echo.
echo Install uWSGI: pip install uwsgi
uwsgi --http localhost:9090 --wsgi-file examples/wsgi/wsgi_example.py --master --processes 4 --enable-threads --threads 2
goto :eof

:wsgi-waitress
echo Starting WSGI server with Waitress...
echo Access: http://localhost:9090/
echo Press Ctrl+C to stop
echo.
echo Install Waitress: pip install waitress
waitress-serve --port=9090 --threads=4 examples.wsgi.wsgi_example:application
goto :eof

:format
echo Formatting code...
black src/ tests/ examples/
isort src/ tests/ examples/
echo Code formatting complete
goto :eof

:lint
echo Running code linting...
ruff check src/ tests/ examples/
echo Code linting complete
goto :eof

:type-check
echo Running type checking...
mypy src/
echo Type checking complete
goto :eof

:check-all
call :format
call :lint
call :type-check
echo All checks complete
goto :eof

:eof
