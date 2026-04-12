"""
Умные теги для задач на основе ключевых слов.
"""
from typing import List


class SmartTagger:
    """Автоматическое определение категорий по тексту задачи."""

    KEYWORDS = {
        'работа': ['работа', 'проект', 'встреча', 'звонок', 'отчёт', 'презентация', 'дедлайн', 'задача', 'клиент', 'совещание'],
        'личное': ['купить', 'дом', 'семья', 'друзья', 'день рождения', 'подарок', 'позвонить', 'написать'],
        'срочно': ['срочно', 'важно', 'asap', 'сегодня', 'немедленно', 'критично'],
        'учёба': ['учёба', 'экзамен', 'лекция', 'курсовая', 'диплом', 'конспект', 'домашка'],
        'здоровье': ['врач', 'аптека', 'лекарство', 'анализы', 'спорт', 'тренировка', 'зал'],
        'финансы': ['оплатить', 'счёт', 'банк', 'налоги', 'деньги', 'перевод', 'платёж'],
    }

    @staticmethod
    def detect_category(text: str) -> str:
        """
        Определить категорию по тексту задачи.

        Args:
            text: текст задачи (title + description)

        Returns:
            категория или 'общее'
        """
        text_lower = text.lower()

        # Подсчитываем совпадения для каждой категории
        scores = {}
        for category, keywords in SmartTagger.KEYWORDS.items():
            score = sum(1 for keyword in keywords if keyword in text_lower)
            if score > 0:
                scores[category] = score

        # Возвращаем категорию с максимальным score
        if scores:
            return max(scores, key=scores.get)

        return 'общее'

    @staticmethod
    def detect_priority(text: str) -> int:
        """
        Определить приоритет по тексту.

        Args:
            text: текст задачи

        Returns:
            1 (высокий), 2 (средний), 3 (низкий)
        """
        text_lower = text.lower()

        # Высокий приоритет
        high_keywords = ['срочно', 'важно', 'asap', 'критично', 'немедленно', '!!!']
        if any(keyword in text_lower for keyword in high_keywords):
            return 1

        # Средний приоритет
        medium_keywords = ['скоро', 'желательно', 'надо', 'нужно']
        if any(keyword in text_lower for keyword in medium_keywords):
            return 2

        # По умолчанию низкий
        return 3

    @staticmethod
    def extract_tags(text: str) -> List[str]:
        """
        Извлечь все подходящие теги из текста.

        Args:
            text: текст задачи

        Returns:
            список тегов
        """
        text_lower = text.lower()
        tags = []

        for category, keywords in SmartTagger.KEYWORDS.items():
            if any(keyword in text_lower for keyword in keywords):
                tags.append(category)

        return tags if tags else ['общее']
