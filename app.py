from flask import Flask, render_template, request, redirect
from kubernetes import client, config
import os
import requests  # 프로메테우스 API 호출을 위해 필요합니다.

app = Flask(__name__)

# [설정] 프로메테우스 서버 주소 (Helm 설치 시 기본 서비스 이름 기준)
# 만약 다른 네임스페이스에 설치했다면 주소를 수정해야 합니다.
PROMETHEUS_URL = "http://prometheus-stack-server.default.svc.cluster.local"

# K8s 설정 로드
try:
    if os.environ.get('KUBERNETES_SERVICE_HOST'):
        config.load_incluster_config()
    else:
        config.load_kube_config()
    v1 = client.CoreV1Api()
except Exception as e:
    print(f"K8s Config Error: {e}")
    v1 = None

def query_prometheus(query):
    """프로메테우스에 PromQL을 날려 결과값을 가져오는 함수"""
    try:
        response = requests.get(f"{PROMETHEUS_URL}/api/v1/query", params={'query': query}, timeout=2)
        results = response.json()['data']['result']
        if results:
            # 결과값 중 수치 데이터만 추출 ([timestamp, value])
            return float(results[0]['value'][1])
        return 0.0
    except Exception as e:
        print(f"Prometheus Query Error: {e}")
        return None

@app.route('/')
def dashboard():
    # 1. K8s 기본 지표 (Pod, Node 개수)
    active_pods_count = "N/A"
    node_count = "N/A"
    if v1:
        try:
            pods = v1.list_pod_for_all_namespaces(watch=False)
            active_pods_count = len(pods.items)
            nodes = v1.list_node()
            node_count = len(nodes.items)
        except Exception as e:
            print(f"K8s API Query Error: {e}")

    # 2. 프로메테우스 실시간 지표 (CPU 사용량 등)
    # 쿼리 설명: 전체 노드의 CPU 평균 사용률을 계산합니다.
    cpu_query = '100 - (avg(irate(node_cpu_seconds_total{mode="idle"}[5m])) * 100)'
    real_cpu = query_prometheus(cpu_query)
    
    # 3. GPU 사용량 (NVIDIA Exporter 설치 시 가능, 없으면 0.0)
    gpu_query = 'avg(DCGM_FI_DEV_GPU_UTIL)'
    real_gpu = query_prometheus(gpu_query)

    # 실험 목록 (샘플 데이터)
    experiments = [
        {"id": "EXP-001", "name": "Auto-Drive-V1", "researcher": "H202601", "status": "Success", "date": "2026-04-04"},
        {"id": "EXP-002", "name": "Sensor-Fusion", "researcher": "H202605", "status": "Running", "date": "2026-04-04"}
    ]

    stats = {
        "active_pods": active_pods_count,
        "nodes": node_count,
        "cpu_usage": f"{real_cpu:.1f}%" if real_cpu is not None else "OFFLINE",
        "gpu_usage": f"{real_gpu:.1f}%" if real_gpu is not None else "0.0%",
        "success_rate": "99.2%"
    }

    return render_template('dashboard.html', stats=stats, experiments=experiments)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
