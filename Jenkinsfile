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
    resources:
      requests: { memory: "512Mi", cpu: "500m" }
      limits: { memory: "1Gi", cpu: "1000m" }
"""
        }
    }

    environment {
        // Seu usuário CORRETO do DockerHub
        DOCKER_REPO = 'pedropvp/projeto-contas'
        TAG_NAME = "${BUILD_NUMBER}"
        
        // Caminho e URL CORRETOS da Infraestrutura
        FILE_HML = 'k8s-platform/workloads/projeto-contas/deployment.yaml'
        GIT_INFRA_URL = 'github.com/DEWNOWxs/kafka_project_kubernetes.git'
    }

    stages {
        stage('Checkout App') {
            steps {
                // Se o repo do Maickson for PÚBLICO, não precisa de credentialsId aqui.
                git branch: 'main', url: 'https://github.com/maicksonmsp/projeto-contas.git'
            }
        }

        stage('Build & Push') {
            steps {
                container('docker') {
                    script {
                        // Wait strategy para o Docker acordar
                        int retries = 0
                        while (sh(script: 'docker info', returnStatus: true) != 0 && retries < 15) {
                            sleep 2
                            retries++
                        }
                        
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
                    // AQUI PRECISA DE AUTENTICAÇÃO SIM! (Para fazer o git push)
                    withCredentials([usernamePassword(credentialsId: 'github-token', usernameVariable: 'GIT_USER', passwordVariable: 'GIT_PASS')]) {
                        sh """
                        git config --global user.email "jenkins@bot.com"
                        git config --global user.name "Jenkins Bot"
                        
                        rm -rf infra_repo
                        
                        # Clona o repo de INFRA (usando senha)
                        git clone https://${GIT_USER}:${GIT_PASS}@${GIT_INFRA_URL} infra_repo
                        cd infra_repo
                        
                        if [ -f ${FILE_HML} ]; then
                            sed -i "s|image: ${DOCKER_REPO}:.*|image: ${DOCKER_REPO}:${TAG_NAME}|g" ${FILE_HML}
                            
                            git add ${FILE_HML}
                            git diff-index --quiet HEAD || git commit -m "Deploy Contas: Build ${TAG_NAME}"
                            
                            # IMPORTANTE: Verifique se sua branch de infra é 'main' ou 'develop'
                            git push origin main
                        else
                            echo "⚠️ Arquivo ${FILE_HML} não encontrado no repo de infra!"
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