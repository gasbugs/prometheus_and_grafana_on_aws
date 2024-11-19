cat <<EOF > nginx.conf
user nginx;
worker_processes auto;

events {
    worker_connections 1024;
}

http {
  server {
    listen 80;
    server_name localhost;
  
    location /nginx_status {
      stub_status on;
      access_log off;
      allow 127.0.0.1;  # 로컬에서만 접근 허용
      deny all;          # 외부 접근 차단
    }
  }
}
EOF

kubectl create configmap nginx-config --from-file=nginx.conf

cat <<EOF | kubectl apply -f -
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: nginx-server
  labels:
    app: nginx
spec:
  replicas: 1
  selector:
    matchLabels:
      app: nginx
  template:
    metadata:
      labels:
        app: nginx
      annotations:
        prometheus.io/scrape: 'true'
        prometheus.io/port: '9113'   # Prometheus가 스크랩할 포트 (Exporter 포트)
    spec:
      containers:
      - name: nginx
        image: nginx:latest
        ports:
        - containerPort: 80
        volumeMounts:
        - name: nginx-config
          mountPath: /etc/nginx/nginx.conf   # Nginx 설정 파일 경로
          subPath: nginx.conf
      - name: nginx-exporter
        image: nginx/nginx-prometheus-exporter:0.10.0
        args:
          - '-nginx.scrape-uri=http://localhost/nginx_status'  # Nginx 상태 페이지 URI 설정
        ports:
        - containerPort: 9113   # Exporter가 노출하는 포트 (Prometheus가 스크랩할 포트)
      volumes:
      - name: nginx-config
        configMap:
          name: nginx-config   # Nginx 설정을 담고 있는 ConfigMap (아래 참조)
---
apiVersion: v1
kind: Service
metadata:
  name: nginx-service
  labels:
    app: nginx
spec:
  ports:
  - name: http
    port: 80         # Nginx 서비스 포트 (웹 트래픽)
    targetPort: 80   # Nginx 컨테이너의 포트와 일치해야 함
  - name: exporter   # Prometheus가 스크랩할 Exporter 포트 추가 
    port: 9113       # Exporter 서비스 포트 (메트릭 스크랩)
    targetPort: 9113 # Exporter 컨테이너의 포트와 일치해야 함 
  selector:
    app: nginx       # Deployment와 동일한 라벨 선택자 사용 
---
apiVersion: monitoring.coreos.com/v1
kind: ServiceMonitor
metadata:
  name: nginx-monitor
  namespace: default
  labels:
    app: nginx
    release: prometheus
spec:
  selector:
    matchLabels:
      app: nginx         # Service와 일치하는 라벨 선택자 사용 
  endpoints:
    - port: exporter     # Service에서 정의한 exporter 포트를 지정 
      interval: 10s      # 메트릭 스크랩 주기 (30초마다)
EOF