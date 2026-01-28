pipeline {
    agent {
        kubernetes {
            yaml """
apiVersion: v1
kind: Pod
metadata:
  labels:
    app: jenkins-python-builder
spec:
  containers:
  - name: docker
    image: docker:24.0.7-cli
    command: ["cat"]
    tty: true
    env: [{ name: DOCKER_HOST, value: "tcp://localhost:2375" }]
    resources:
      requests: { memory: "128Mi", cpu: "50m" }
      limits: { memory: "256Mi", cpu: "200m" }
  - name: dind-daemon
    image: docker:24.0.7-dind
    securityContext: { privileged: true }
    env: [{ name: DOCKER_TLS_CERTDIR, value: "" }]
    # --- AJUSTE 1: Aumentei a memória para o Docker aguentar o tranco ---
    resources:
      requests: { memory: "512Mi", cpu: "500m" }
      limits: { memory: "1Gi", cpu: "1000m" }
"""
        }
    }

    environment {
        DOCKER_REPO = 'dockerhub-pedro/projeto-contas'
        TAG_NAME = "${BUILD_NUMBER}"
        FILE_HML = 'k8s-platform/workloads/projeto-contas/deployment.yaml'
        GIT_INFRA_URL = 'github.com/DEWNOWxs/kafka_project_kubernetes.git'
    }

    stages {
        stage('Checkout App') {
            steps {
                git branch: 'main', credentialsId: 'github-token', url: 'https://github.com/maicksonmsp/projeto-contas.git'
            }
        }

        stage('Build & Push') {
            steps {
                container('docker') {
                    script {
                        // --- AJUSTE 2: Loop de Espera (Wait Strategy) ---
                        // Tenta conectar no Docker por até 30 segundos antes de falhar
                        int retries = 0
                        while (sh(script: 'docker info', returnStatus: true) != 0 && retries < 15) {
                            echo "⏳ Aguardando Docker Daemon iniciar (Tentativa ${retries+1}/15)..."
                            sleep 2
                            retries++
                        }
                        
                        // Se saiu do loop e ainda falha, aí sim erro real
                        if (sh(script: 'docker info', returnStatus: true) != 0) {
                            error "❌ O Docker Daemon não iniciou. Verifique se o Pod tem memória suficiente."
                        }

                        echo "✅ Docker conectado! Iniciando build..."

                        docker.withRegistry('', 'dockerhub-pedro') {
                            def img = docker.build("${DOCKER_REPO}:${TAG_NAME}")
                            img.push()
                            img.push('latest')
                        }
                    }
                }
            }
        }

        stage('Deploy GitOps') {
            steps {
                script {
                    withCredentials([usernamePassword(credentialsId: 'github-token', usernameVariable: 'GIT_USER', passwordVariable: 'GIT_PASS')]) {
                        sh """
                        git config --global user.email "jenkins@bot.com"
                        git config --global user.name "Jenkins Bot"
                        
                        # Limpa pasta antiga se existir
                        rm -rf infra_repo
                        
                        git clone https://${GIT_USER}:${GIT_PASS}@${GIT_INFRA_URL} infra_repo
                        cd infra_repo
                        
                        if [ -f ${FILE_HML} ]; then
                            sed -i "s|image: ${DOCKER_REPO}:.*|image: ${DOCKER_REPO}:${TAG_NAME}|g" ${FILE_HML}
                            
                            git add ${FILE_HML}
                            # Commit condicional (só comita se tiver mudança)
                            git diff-index --quiet HEAD || git commit -m "Deploy Contas: Build ${TAG_NAME}"
                            git push origin develop
                        else
                            echo "⚠️ Arquivo ${FILE_HML} não encontrado. Pulando update."
                            ls -R
                            exit 1
                        fi
                        """
                    }
                }
            }
        }
    }
}