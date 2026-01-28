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
  - name: dind-daemon
    image: docker:24.0.7-dind
    securityContext: { privileged: true }
    env: [{ name: DOCKER_TLS_CERTDIR, value: "" }]
"""
        }
    }

    environment {
        // Nome da imagem no Docker Hub
        DOCKER_REPO = 'dockerhub-pedro/projeto-contas'
        TAG_NAME = "${BUILD_NUMBER}"
        
        // Caminho do arquivo no repo de INFRA
        FILE_HML = 'k8s-platform/workloads/projeto-contas/deployment.yaml'
        
        // URL do repo de INFRA
        GIT_INFRA_URL = 'github.com/DEWNOWxs/kafka_project_kubernetes.git'
    }

    stages {
        stage('Checkout App') {
            steps {
                // Pega o código do app Python
                git branch: 'main', credentialsId: 'github-token', url: 'https://github.com/maicksonmsp/projeto-contas.git'
            }
        }

        stage('Build & Push') {
            steps {
                container('docker') {
                    script {
                        docker.withRegistry('', 'dockerhub-pedro') {
                            // Builda usando o Dockerfile blindado
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
                        git config user.email "jenkins@bot.com" && git config user.name "Jenkins Bot"
                        
                        # Clona infra
                        git clone https://${GIT_USER}:${GIT_PASS}@${GIT_INFRA_URL} infra_repo
                        cd infra_repo
                        
                        # Atualiza a imagem no YAML
                        if [ -f ${FILE_HML} ]; then
                            sed -i "s|image: ${DOCKER_REPO}:.*|image: ${DOCKER_REPO}:${TAG_NAME}|g" ${FILE_HML}
                            
                            git add ${FILE_HML}
                            git commit -m "Deploy Contas: Build ${TAG_NAME}" --allow-empty
                            git push origin develop
                        else
                            echo "ERRO: Crie o arquivo deployment.yaml no repo de infra antes!"
                            exit 1
                        fi
                        """
                    }
                }
            }
        }
    }
}