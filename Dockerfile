FROM ubuntu:20.04

# Evitar interações durante a instalação
ENV DEBIAN_FRONTEND=noninteractive

# Instalar dependências
RUN apt-get update && apt-get install -y \
    python3 \
    python3-pip \
    git \
    zip \
    unzip \
    openjdk-8-jdk \
    wget \
    libssl-dev \
    autoconf \
    libtool \
    pkg-config \
    zlib1g-dev \
    libncurses5-dev \
    libncursesw5-dev \
    cmake \
    libffi-dev \
    build-essential \
    cython3 \
    python3-dev \
    python3-setuptools \
    python3-wheel \
    && rm -rf /var/lib/apt/lists/*

# Configurar ambiente Python
ENV PYTHONPATH=/usr/lib/python3/dist-packages
ENV PATH="/usr/local/bin:${PATH}"

# Instalar pip e setuptools
RUN python3 -m pip install --upgrade pip==23.3.2 setuptools==68.2.2

# Instalar Buildozer e suas dependências
RUN pip3 install --no-cache-dir \
    pexpect==4.8.0 \
    virtualenv==20.24.3 \
    buildozer==1.5.0 \
    cython==0.29.36

# Configurar ambiente Android
ENV ANDROID_HOME="/opt/android" \
    ANDROID_SDK_HOME="/opt/android" \
    ANDROID_NDK_HOME="/opt/android/android-ndk-r25b" \
    PATH="/opt/android/cmdline-tools/latest/bin:/opt/android/tools:/opt/android/platform-tools:/opt/android/android-ndk-r25b:${PATH}" \
    # Evitar avisos do Buildozer
    BUILDOZER_NONINTERACTIVE=1 \
    # Configurar APIs do Android
    ANDROIDAPI=33 \
    ANDROIDMINAPI=21

# Criar diretórios necessários e instalar Android SDK
RUN mkdir -p /opt/android && \
    cd /opt/android && \
    # Baixar e extrair Android SDK
    echo "Baixando Android Command Line Tools..." && \
    wget -q https://dl.google.com/android/repository/commandlinetools-linux-8512546_latest.zip && \
    echo "Extraindo Android Command Line Tools..." && \
    unzip -q commandlinetools-linux-8512546_latest.zip && \
    rm commandlinetools-linux-8512546_latest.zip && \
    # Verificar estrutura após extração
    echo "Conteúdo do diretório após extração:" && \
    ls -la && \
    # Verificar estrutura do cmdline-tools
    echo "Conteúdo do diretório cmdline-tools:" && \
    ls -la cmdline-tools && \
    # Verificar se o diretório latest existe
    if [ ! -d "cmdline-tools/latest" ]; then \
        echo "Criando diretório latest" && \
        mkdir -p cmdline-tools/latest && \
        mv cmdline-tools/* cmdline-tools/latest/ 2>/dev/null || true; \
    fi && \
    # Verificar estrutura final
    echo "Estrutura final do cmdline-tools:" && \
    ls -la cmdline-tools/latest && \
    # Baixar e extrair Android NDK
    echo "Baixando Android NDK..." && \
    wget -q https://dl.google.com/android/repository/android-ndk-r25b-linux.zip && \
    echo "Extraindo Android NDK..." && \
    unzip -q android-ndk-r25b-linux.zip && \
    rm android-ndk-r25b-linux.zip && \
    # Configurar PATH e instalar SDK
    echo "Configurando PATH..." && \
    export PATH="/opt/android/cmdline-tools/latest/bin:${PATH}" && \
    echo "PATH atual: $PATH" && \
    # Verificar versão do sdkmanager
    echo "Verificando versão do sdkmanager..." && \
    sdkmanager --version && \
    # Listar pacotes disponíveis
    echo "Listando pacotes disponíveis..." && \
    sdkmanager --list && \
    # Aceitar licenças
    echo "Aceitando licenças..." && \
    yes | sdkmanager --licenses && \
    # Instalar plataformas e ferramentas
    echo "Instalando plataformas e ferramentas..." && \
    sdkmanager --verbose \
        "platform-tools" \
        "platforms;android-33" \
        "build-tools;33.0.0" \
        "extras;android;m2repository" \
        "extras;google;m2repository" \
        "extras;google;google_play_services" && \
    # Verificar instalação
    echo "Verificando instalação..." && \
    sdkmanager --list | grep "installed" && \
    # Verificar diretório de plataformas
    echo "Conteúdo do diretório platforms:" && \
    ls -la /opt/android/platforms

# Criar usuário não-root
RUN useradd -m -s /bin/bash builder && \
    mkdir -p /app && \
    chown -R builder:builder /app /opt/android

# Mudar para o usuário não-root
USER builder

# Definir diretório de trabalho
WORKDIR /app

# Copiar apenas os arquivos necessários
COPY --chown=builder:builder requirements.txt .
COPY --chown=builder:builder main.py .
COPY --chown=builder:builder buildozer.spec .

# Comando padrão
CMD ["buildozer", "android", "debug"] 