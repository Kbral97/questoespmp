# Construir a imagem Docker
docker build -t questoespmp-build .

# Executar o container e fazer o build
docker run --rm -v ${PWD}:/app questoespmp-build 