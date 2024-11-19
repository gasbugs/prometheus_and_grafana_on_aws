# eksctl 명령을 실행하여 kubectl config 설정
resource "null_resource" "eks_kubectl_config" {
  provisioner "local-exec" {
    command = "eksctl utils write-kubeconfig --cluster ${module.eks.cluster_name} --region ${var.aws_region}"
  }

  depends_on = [module.eks]
}

provider "helm" {
  kubernetes {
    config_path = "${pathexpand("~")}/.kube/config"
  }
}

# Helm 차트 설치
resource "helm_release" "kube-prometheus-stack" {
  name             = "kube-prometheus-stack"
  repository       = "https://prometheus-community.github.io/helm-charts"
  chart            = "kube-prometheus-stack"
  namespace        = "monitoring"
  create_namespace = true
  values           = [file("kube-prom-vaules.yaml")]

  # 강제 업데이트를 위해 다음을 추가할 수 있습니다
  force_update = true

  depends_on = [null_resource.eks_kubectl_config]
}
