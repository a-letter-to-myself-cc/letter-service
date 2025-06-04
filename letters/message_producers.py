# letters/message_producers.py

import pika
import json
from django.conf import settings # settings.py의 RabbitMQ 호스트 정보 등을 사용하기 위해

def publish_emotion_analysis_request(letter_id: int, user_id: int, content: str) -> bool:
    """
    편지 내용을 받아 감정 분석 요청을 RabbitMQ로 발행
    """
    try:
        # settings.py에 RABBITMQ_HOST가 정의되어 있다고 가정, 없으면 'localhost' 사용
        rabbitmq_host = getattr(settings, 'RABBITMQ_HOST', 'localhost')
        rabbitmq_port = getattr(settings, 'RABBITMQ_PORT', 5672) # 기본 포트 5672
        rabbitmq_vhost = getattr(settings, 'RABBITMQ_VHOST', '/')
        rabbitmq_user = getattr(settings, 'RABBITMQ_USER', 'guest')
        rabbitmq_password = getattr(settings, 'RABBITMQ_PASSWORD', 'guest')
        
        credentials = pika.PlainCredentials(rabbitmq_user, rabbitmq_password)
        connection_params = pika.ConnectionParameters(
            host=rabbitmq_host,
            port=rabbitmq_port,
            virtual_host=rabbitmq_vhost,
            credentials=credentials
        )
        
        print(f"📨 프로듀서: RabbitMQ 접속 시도 중... {rabbitmq_host}:{rabbitmq_port}") # 디버깅용
        connection = pika.BlockingConnection(connection_params)
        channel = connection.channel()
        print("✨ 프로듀서: RabbitMQ 접속 및 채널 생성 완료.") # 디버깅용

        # 익스체인지 선언
        # durable=True는 RabbitMQ 서버가 재시작되어도 익스체인지가 유지되도록 합니다.
        channel.exchange_declare(exchange='emotion.direct', exchange_type='direct', durable=False)
        print("🔄 프로듀서: Exchange 'emotion.direct' (durable=False) 선언 완료.") # 디버깅용

        message_body = {
            "letter_id": letter_id,
            "user_id": user_id,
            "content": content
            # 필요하다면 추가 정보 (예: user_id, 생성 시간 등)
        }
        
        # 메시지 발행
        channel.basic_publish(
            exchange='emotion.direct',
            routing_key='analyze', # emotion_analysis 서비스의 컨슈머가 이 라우팅 키를 사용
            body=json.dumps(message_body),
            properties=pika.BasicProperties(
               # delivery_mode=pika.spec.PERSISTENT_DELIVERY_MODE, # 메시지 지속성 (큐도 durable이어야 효과)
                content_type='application/json', # 메시지 내용이 JSON임을 명시
            )
        )
        
        print(f"✅ 프로듀서: Letter ID {letter_id} 감정 분석 요청 발행 성공.")
        connection.close()
        return True

    except pika.exceptions.AMQPConnectionError as e:
        # RabbitMQ 연결 실패 시 오류 처리 (실제 운영에서는 로깅 및 알림/재시도 전략 필요)
        print(f"❌ 프로듀서 ERROR: RabbitMQ 접속 실패 ({rabbitmq_host}) - {e}")
        return False
    except Exception as e:
        # 기타 예외 처리
        print(f"❌ 프로듀서 ERROR: Letter ID {letter_id} 메시지 발행 실패 - {e}")
        return False