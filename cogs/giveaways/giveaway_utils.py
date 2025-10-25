import json
import os
from typing import Dict, Optional
import disnake
from datetime import datetime, timedelta

class GiveawayManager:
    def __init__(self):
        self.giveaway_file = 'data/giveaways.json'

    async def load_giveaways(self) -> Dict:
        """Загрузка активных розыгрышей"""
        try:
            with open(self.giveaway_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            return {}
            
    async def save_giveaway(self, message_id: int, data: Dict):
        """Сохранение розыгрыша"""
        giveaways = await self.load_giveaways()
        giveaways[str(message_id)] = data
        self._save_data(giveaways)
        
    async def remove_giveaway(self, message_id: int):
        """Удаление розыгрыша"""
        giveaways = await self.load_giveaways()
        if str(message_id) in giveaways:
            del giveaways[str(message_id)]
            self._save_data(giveaways)
            
    def _save_data(self, data: Dict):
        with open(self.giveaway_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4, ensure_ascii=False)

    def format_time(self, seconds: int) -> str:
        """Форматирование времени"""
        days = seconds // (24 * 3600)
        seconds %= 24 * 3600
        hours = seconds // 3600
        seconds %= 3600
        minutes = seconds // 60
        seconds %= 60
        
        parts = []
        if days > 0:
            parts.append(f"{days}д")
        if hours > 0:
            parts.append(f"{hours}ч")
        if minutes > 0:
            parts.append(f"{minutes}м")
        if seconds > 0:
            parts.append(f"{seconds}с")
            
        return " ".join(parts) if parts else "0с"