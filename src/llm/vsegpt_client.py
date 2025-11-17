# src/llm/vsegpt_client.py

import requests
from typing import Optional, Dict, List
import logging
import json

logger = logging.getLogger(__name__)


class VseGPTClient:
    """Клиент для работы с VseGPT API"""
    
    def __init__(self, api_key: str, model: Optional[str] = None, api_base_url: Optional[str] = None):
        self.api_key = api_key
        self.base_url = (api_base_url or "https://api.vsegpt.ru/v1").rstrip()
        
        try:
            from config.settings import settings
            self.model = model or getattr(settings, 'VSE_GPT_MODEL', "openai/gpt-4o-mini")
        except:
            self.model = model or "openai/gpt-4o-mini"
        
        if self.base_url != self.base_url.strip():
            raise ValueError(
                f"КРИТИЧЕСКАЯ ОШИБКА: base_url содержит пробелы!\n"
                f"URL: {repr(self.base_url)}\n"
                f"Длина: {len(self.base_url)}"
            )
        
        if not self.base_url.endswith("v1"):
            raise ValueError(
                f"ОШИБКА: base_url должен заканчиваться на 'v1'!\n"
                f"Текущий URL: {repr(self.base_url)}"
            )
        
        if not api_key or api_key.strip() == "":
            raise ValueError("API ключ не может быть пустым!")
        
        logger.debug(f"✅ VseGPTClient инициализирован. URL: {self.base_url}, Model: {self.model}")
    
    def ask(
        self,
        prompt: Optional[str] = None,
        messages: Optional[List[Dict[str, str]]] = None,
        temperature: float = 0.3,
        max_tokens: int = 500,
        system_prompt: Optional[str] = None
    ) -> Optional[str]:
        """Универсальный метод отправки запросов к VseGPT API"""
        
        if prompt is None and messages is None:
            raise ValueError("Требуется prompt или messages")
        if prompt is not None and messages is not None:
            raise ValueError("Нельзя указывать prompt и messages одновременно")
        
        if messages is not None:
            final_messages = messages
            logger.info(f"📤 Используется массив из {len(messages)} сообщений")
        else:
            final_messages = []
            if system_prompt:
                final_messages.append({"role": "system", "content": system_prompt})
            else:
                final_messages.append({
                    "role": "system",
                    "content": "Ты — профессиональный AI-ассистент. Отвечай кратко, точно и структурированно."
                })
            final_messages.append({"role": "user", "content": prompt})
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": self.model,
            "messages": final_messages,
            "temperature": temperature,
            "max_tokens": max_tokens
        }
        
        try:
            logger.info(f"🚀 Отправка запроса к VseGPT (model: {self.model})")
            logger.debug(f"📋 Payload: {json.dumps(payload, ensure_ascii=False, indent=2)[:500]}...")
            
            response = requests.post(
                f"{self.base_url}/chat/completions",
                headers=headers,
                json=payload,
                timeout=30
            )
            
            if response.status_code == 400:
                logger.error("=" * 80)
                logger.error("❌ ОШИБКА 400: Bad Request")
                logger.error("=" * 80)
                
                try:
                    error_data = response.json()
                    logger.error(f"📄 Полный ответ сервера:")
                    logger.error(json.dumps(error_data, ensure_ascii=False, indent=2))
                    
                    if "error" in error_data:
                        error_msg = error_data["error"]
                        if isinstance(error_msg, dict):
                            logger.error(f"❌ Тип ошибки: {error_msg.get('type', 'unknown')}")
                            logger.error(f"❌ Сообщение: {error_msg.get('message', 'нет описания')}")
                            logger.error(f"❌ Код: {error_msg.get('code', 'нет кода')}")
                        else:
                            logger.error(f"❌ Ошибка: {error_msg}")
                except:
                    logger.error(f"📄 Тело ответа (raw): {response.text[:1000]}")
                
                logger.error("=" * 80)
                logger.error("🔧 ВОЗМОЖНЫЕ ПРИЧИНЫ:")
                logger.error("1. Неверный API ключ")
                logger.error("2. Закончились токены на балансе")
                logger.error("3. Неверное имя модели (текущая: {})".format(self.model))
                logger.error("4. Превышен лимит запросов")
                logger.error("5. Некорректный формат сообщений")
                logger.error("=" * 80)
                logger.error("💡 РЕШЕНИЕ:")
                logger.error("1. Проверьте баланс на https://api.vsegpt.ru")
                logger.error("2. Проверьте API ключ в .env или config/settings.py")
                logger.error("3. Попробуйте другую модель (gpt-4o вместо gpt-4o-mini)")
                logger.error("=" * 80)
                
                return None
            
            response.raise_for_status()
            data = response.json()
            
            if "choices" not in data or not data["choices"]:
                logger.error(f"❌ Некорректный ответ (нет choices): {data}")
                return None
            
            if "message" not in data["choices"][0]:
                logger.error(f"❌ Отсутствует message в choices: {data}")
                return None
            
            answer = data["choices"][0]["message"]["content"]
            
            if "usage" in data:
                usage = data["usage"]
                logger.info(
                    f"📊 Токены: prompt={usage.get('prompt_tokens', 0)}, "
                    f"completion={usage.get('completion_tokens', 0)}, "
                    f"total={usage.get('total_tokens', 0)}"
                )
            
            logger.info(f"✅ Получен ответ ({len(answer)} символов)")
            return answer
            
        except requests.exceptions.Timeout:
            logger.error("❌ Таймаут при обращении к VseGPT API (>30 сек)")
            logger.error("💡 Попробуйте позже или проверьте интернет-соединение")
            return None
        
        except requests.exceptions.HTTPError as e:
            status = e.response.status_code if e.response else "unknown"
            logger.error(f"❌ HTTP ошибка VseGPT API: {status} {e}")
            
            if e.response:
                try:
                    error_data = e.response.json()
                    if "error" in error_data:
                        logger.error(f"📋 Детали: {error_data['error']}")
                except:
                    logger.error(f"📄 Ответ сервера: {e.response.text[:500]}")
            
            return None
        
        except requests.exceptions.ConnectionError as e:
            logger.error(f"❌ Ошибка соединения: {e}")
            logger.error("💡 Проверьте интернет-соединение")
            return None
        
        except requests.exceptions.RequestException as e:
            logger.error(f"❌ Ошибка сети: {e}")
            return None
        
        except json.JSONDecodeError as e:
            logger.error(f"❌ Ошибка парсинга JSON ответа: {e}")
            logger.error(f"📄 Ответ сервера: {response.text[:500] if 'response' in locals() else 'нет данных'}")
            return None
        
        except Exception as e:
            logger.error(f"❌ Неожиданная ошибка: {type(e).__name__}: {e}")
            import traceback
            logger.error(f"📋 Traceback: {traceback.format_exc()}")
            return None
    
    def ask_simple(self, prompt: str, temperature: float = 0.3, max_tokens: int = 500) -> Optional[str]:
        """Упрощенный метод для быстрых запросов"""
        return self.ask(prompt=prompt, temperature=temperature, max_tokens=max_tokens)
    
    def test_connection(self) -> bool:
        """Проверка работоспособности API ключа"""
        logger.info("🔍 Проверка подключения к VseGPT API...")
        
        try:
            response = self.ask(prompt="Ответь одним словом: работает", max_tokens=10)
            if response:
                logger.info("✅ VseGPT API работает корректно")
                logger.info(f"📝 Тестовый ответ: {response}")
                return True
            else:
                logger.error("❌ VseGPT API не вернул ответ")
                return False
        except Exception as e:
            logger.error(f"❌ Ошибка при тестировании VseGPT API: {e}")
            return False
    
    def get_models(self) -> List[str]:
        """Список доступных моделей"""
        return [
            "openai/gpt-4o-mini",
            "openai/gpt-4o",
            "anthropic/claude-3.5-sonnet"
        ]
    
    def set_model(self, model: str):
        """Установка модели"""
        if model not in self.get_models():
            logger.warning(f"⚠️ Модель {model} может быть недоступна")
        
        self.model = model
        logger.info(f"✅ Модель изменена на: {model}")


def get_vsegpt_client(api_key: str, model: str = "openai/gpt-4o-mini") -> VseGPTClient:
    """Создание экземпляра VseGPT клиента"""
    return VseGPTClient(api_key=api_key, model=model)


def _auto_test():
    """Автоматический тест при импорте модуля"""
    try:
        client = VseGPTClient("test_key")
        
        assert client.base_url == client.base_url.strip(), "URL содержит пробелы!"
        assert client.base_url.endswith("v1"), "URL не заканчивается на v1!"
        
        test_url = f"{client.base_url}/chat/completions"
        assert " /" not in test_url, "Пробел перед /chat/completions!"
        
        logger.debug("✅ Автотест base_url пройден")
        return True
    except Exception as e:
        logger.error(f"❌ Автотест провален: {e}")
        return False


if __name__ != "__main__":
    _auto_test()


if __name__ == "__main__":
    print("=" * 80)
    print("🧪 ТЕСТЫ vsegpt_client.py")
    print("=" * 80)
    print()
    
    print("Тест 1: Проверка base_url")
    client = VseGPTClient("test_key")
    print(f"  URL: {repr(client.base_url)}")
    print(f"  Длина: {len(client.base_url)}")
    print(f"  Без пробелов: {client.base_url == client.base_url.strip()}")
    print(f"  Заканчивается на v1: {client.base_url.endswith('v1')}")
    print(f"  Итоговый URL: {client.base_url}/chat/completions")
    assert client.base_url == client.base_url.strip()
    assert client.base_url.endswith("v1")
    print("  ✅ PASSED\n")
    
    print("Тест 2: Валидация параметров")
    try:
        client.ask()
        print("  ❌ FAILED\n")
    except ValueError:
        print("  ✅ PASSED\n")
    
    print("Тест 3: Создание через фабрику")
    client2 = get_vsegpt_client("test_key_2")
    assert client2.api_key == "test_key_2"
    print("  ✅ PASSED\n")
    
    print("=" * 80)
    print("✅ ВСЕ ТЕСТЫ ПРОЙДЕНЫ")
    print("=" * 80)
    print()
    print(f"Итоговый URL для API запросов:")
    print(f"  {client.base_url}/chat/completions")