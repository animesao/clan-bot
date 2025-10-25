import disnake
from disnake.ext import commands
from datetime import datetime, timedelta
import json
import os
from pathlib import Path

class Trading(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        # --- Data Management ---
        self.data_dir = Path("data")
        self.data_dir.mkdir(exist_ok=True) # Create data directory if it doesn't exist
        self.data_file = self.data_dir / "trading.json"

        # Load trading data
        self.trading_data = self.load_trading_data()
        # Ensure essential structure exists in loaded data
        self.trading_data.setdefault('marketplace', {
            'category_id': None,
            'category_channels': {},
            'general_channel_id': None
        })
        self.trading_data.setdefault('trades', {})

        self.marketplace_data = self.trading_data['marketplace'] # Still use this for convenience

    def load_trading_data(self):
        """Loads trading data from trading.json"""
        if self.data_file.exists():
            try:
                with open(self.data_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except json.JSONDecodeError:
                print(f"Warning: Could not decode JSON from {self.data_file}. Starting with empty data.")
                return {}
            except Exception as e:
                print(f"Error loading trading data from {self.data_file}: {e}")
                return {}
        else:
            return {} # Return empty data if file doesn't exist

    def save_trading_data(self):
        """Saves trading data to trading.json"""
        try:
            with open(self.data_file, 'w', encoding='utf-8') as f:
                json.dump(self.trading_data, f, indent=4, ensure_ascii=False)
        except Exception as e:
            print(f"Error saving trading data to {self.data_file}: {e}")

    async def ensure_marketplace_setup(self, guild):
        # Ensure marketplace category exists
        marketplace_category = disnake.utils.get(guild.categories, id=self.marketplace_data['category_id'])
        if not marketplace_category:
            # Set permissions for @everyone: can view, cannot send messages
            overwrites = {
                guild.default_role: disnake.PermissionOverwrite(
                    read_messages=True,
                    send_messages=False,
                    add_reactions=True, # Allow using buttons/reactions
                    use_external_emojis=True # Allow using custom emojis on reactions/buttons
                )
            }
            marketplace_category = await guild.create_category("💹 Торговая Площадка", overwrites=overwrites)
            self.marketplace_data['category_id'] = marketplace_category.id
            self.save_trading_data()

        # Ensure general marketplace channel exists
        general_channel = guild.get_channel(self.marketplace_data['general_channel_id'])
        if not general_channel:
            # Permissions for channel should inherit from category, but explicitly setting for safety
            overwrites = {
                guild.default_role: disnake.PermissionOverwrite(
                    read_messages=True,
                    send_messages=False,
                    add_reactions=True,
                    use_external_emojis=True
                )
            }
            general_channel = await marketplace_category.create_text_channel("общий-рынок", topic="Общая торговая площадка", overwrites=overwrites)
            self.marketplace_data['general_channel_id'] = general_channel.id
            self.save_trading_data()

        # Ensure specific category channels exist
        await self.ensure_category_channels(marketplace_category)

    async def ensure_category_channels(self, marketplace_category):
        categories = {
            "👔 Костюмы": "Торговля костюмами и одеждой",
            "💣 Оружие": "Торговля оружием и боеприпасами",
            "✨ Артефакты": "Торговля артефактами и редкими предметами",
            "📏 Обвесы": "Торговля обвесами и модификациями",
            "💊 Медицина": "Торговля медикаментами и расходниками",
            "⚒️ Крафт": "Торговля материалами для крафта",
            "📦 Прочее": "Прочие предметы и услуги"
        }
        
        changes_made = False
        for category_name, topic in categories.items():
            if category_name not in self.marketplace_data['category_channels'] or not marketplace_category.guild.get_channel(self.marketplace_data['category_channels'].get(category_name)):
                # Permissions for channel should inherit from category, but explicitly setting for safety
                overwrites = {
                    marketplace_category.guild.default_role: disnake.PermissionOverwrite(
                        read_messages=True,
                        send_messages=False,
                        add_reactions=True,
                        use_external_emojis=True
                    )
                }
                channel = await marketplace_category.create_text_channel(
                    category_name.lower().replace(" ", "-"),
                    topic=topic,
                    overwrites=overwrites # Apply overwrites
                )
                self.marketplace_data['category_channels'][category_name] = channel.id
                changes_made = True
        if changes_made:
            self.save_trading_data()

    @commands.slash_command(
        name="createtrade",
        description="Создать торговое предложение"
    )
    async def create_trade(
        self,
        inter: disnake.ApplicationCommandInteraction,
        item_name: str = commands.Param(description="Название предмета"),
        item_description: str = commands.Param(description="Описание предмета"),
        price: int = commands.Param(description="Цена предмета"),
        category: str = commands.Param(
            description="Категория предмета",
            choices=["👔 Костюмы", "💣 Оружие", "✨ Артефакты", "📏 Обвесы", "💊 Медицина", "⚒️ Крафт", "📦 Прочее"]
        ),
        image_urls: str = commands.Param(description="Ссылки на изображения предмета (обязательно, через запятую)"),
        duration: int = commands.Param(description="Длительность предложения в часах", default=24)
    ):
        await inter.response.defer(ephemeral=True)

        # Split and validate image URLs
        urls = [url.strip() for url in image_urls.split(',')]
        valid_urls = []
        for url in urls:
            if url.startswith(('http://', 'https://')):
                valid_urls.append(url)
            else:
                await inter.edit_original_response(content=f"❌ Некорректная ссылка на изображение: {url}\nВсе ссылки должны начинаться с http:// или https://")
                return

        if not valid_urls:
            await inter.edit_original_response(content="❌ Пожалуйста, предоставьте хотя бы одну корректную ссылку на изображение")
            return

        # Ensure marketplace setup is complete
        await self.ensure_marketplace_setup(inter.guild)

        # Get the target channel based on the selected category
        target_channel_id = self.marketplace_data['category_channels'].get(category)
        if not target_channel_id:
            target_channel_id = self.marketplace_data['general_channel_id']

        target_channel = inter.guild.get_channel(target_channel_id)
        if not target_channel:
            await inter.edit_original_response(content="❌ Произошла ошибка при определении канала для публикации.")
            return

        # Create trade offer
        trade_id = f"{inter.author.id}_{datetime.now().timestamp()}"
        trade = {
            'id': trade_id,
            'seller': str(inter.author.id),
            'item_name': item_name,
            'item_description': item_description,
            'price': price,
            'category': category,
            'image_urls': valid_urls,
            'created_at': datetime.now().isoformat(),
            'expires_at': (datetime.now() + timedelta(hours=duration)).isoformat(),
            'status': 'active'
        }

        # Create embed with trade information
        embed = disnake.Embed(
            title=f"🛍️ Объявление об обмене",
            description=f"**Название предмета:** {item_name}\n\n"
                       f"**Описание объявления:**\n{item_description}\n\n"
                       f"**Автор объявления:** {inter.author.mention}",
            color=disnake.Color(0x23272A) # Dark grey color to match the screenshot theme
        )
        embed.add_field(
            name="💰 Цена предмета:", # Add emoji to field name
            value=f"{price} монет",
            inline=True
        )
        # Add empty field for spacing/alignment if needed (optional)
        # embed.add_field(name="\u200b", value="\u200b", inline=True)
        embed.add_field(
            name="⏰ Действует до:",
            value=f"<t:{int(datetime.fromisoformat(trade['expires_at']).timestamp())}:R>",
            inline=True
        )
        # Set the first image as the main image
        if valid_urls:
            embed.set_image(url=valid_urls[0])
            # Add additional images as fields if there are more than one
            if len(valid_urls) > 1:
                additional_images = "\n".join([f"[Изображение {i+2}]({url})" for i, url in enumerate(valid_urls[1:])])
                embed.add_field(name="📸 Дополнительные изображения:", value=additional_images, inline=False)
        embed.set_footer(text=f"ID предложения: {trade_id} • Опубликовано: {datetime.now().strftime('%Y-%m-%d %H:%M')}") # More descriptive footer
        embed.set_thumbnail(url=inter.author.display_avatar.url)

        # Add buttons
        class TradeButtons(disnake.ui.View):
            def __init__(self, cog, trade_id):
                super().__init__(timeout=None)
                self.cog = cog
                self.trade_id = trade_id # Store trade_id
                # Add a unique custom_id for persistence
                self.custom_id = f"trade_view:{trade_id}"

            @disnake.ui.button(label="Купить", style=disnake.ButtonStyle.green, emoji="💰")
            async def buy_button(self, button: disnake.ui.Button, interaction: disnake.MessageInteraction):
                await interaction.response.defer(ephemeral=True)

                # Find the trade
                trade_id = None
                for tid, trade in self.cog.trading_data['trades'].items():
                    if trade.get('message_id') == interaction.message.id:
                        trade_id = tid
                        break

                if not trade_id:
                    await interaction.edit_original_response(content="❌ Торговое предложение не найдено.")
                    return

                trade = self.cog.trading_data['trades'][trade_id]

                # Prevent seller from showing interest in their own item
                if str(interaction.user.id) == trade['seller']:
                    await interaction.edit_original_response(content="❌ Вы не можете проявить интерес к своему собственному предмету!")
                    return

                # Get buyer user object
                buyer = interaction.user

                # Initialize interested_users list if it doesn't exist
                if 'interested_users' not in trade:
                    trade['interested_users'] = []

                # Check if user has already shown interest
                if str(buyer.id) in trade['interested_users']:
                    await interaction.edit_original_response(content="Вы уже проявили интерес к этому предложению.")
                    return

                # Add user to interested_users list
                trade['interested_users'].append(str(buyer.id))
                self.cog.save_trading_data()

                # Notify seller (via DM for now)
                seller = self.cog.bot.get_user(int(trade['seller']))
                if seller:
                    try:
                        # Format interest notification as an embed
                        interest_embed = disnake.Embed(
                            title=f"👋 Новый интерес к вашему предложению!",
                            description=f"Пользователь {buyer.mention} проявил интерес к вашему предмету:\n\n"
                                       f"**🛍️ Предмет:** {trade['item_name']}\n"
                                       f"**💰 Цена:** {trade['price']} монет\n\n"
                                       f"*Используйте `/viewinterest {trade_id}` для просмотра всех заинтересованных и `/manageinterest` для управления.*",
                            color=disnake.Color.blue()
                        )
                        if trade.get('image_urls'):
                            interest_embed.set_image(url=trade['image_urls'][0]) # Use first image as thumbnail
                        await seller.send(embed=interest_embed)

                    except disnake.Forbidden:
                         print(f"Could not send interest notification DM to seller {seller.id}.")

                await interaction.edit_original_response(content="✅ Ваш интерес к этому предложению зарегистрирован. Продавец уведомлен.")

            @disnake.ui.button(label="Отменить объявление", style=disnake.ButtonStyle.red, emoji="❌")
            async def cancel_button(self, button: disnake.ui.Button, interaction: disnake.MessageInteraction):
                await interaction.response.defer(ephemeral=True)
                # Use self.trade_id to get the trade
                trade = self.cog.trading_data['trades'].get(self.trade_id)

                if not trade:
                    await interaction.edit_original_response(content="❌ Торговое предложение не найдено.")
                    return

                # Pass the trade_id to cancel_trade_message
                await self.cog.cancel_trade_message(interaction, self.trade_id)

            @disnake.ui.button(label="Профиль автора объявления", style=disnake.ButtonStyle.blurple, emoji="👤")
            async def author_profile_button(self, button: disnake.ui.Button, interaction: disnake.MessageInteraction):
                await interaction.response.defer()
                
                # Find the trade using the stored trade_id
                trade = self.cog.trading_data['trades'].get(self.trade_id)

                if not trade:
                    await interaction.edit_original_response(content="❌ Торговое предложение не найдено.")
                    return

                seller = self.cog.bot.get_user(int(trade['seller']))

                if not seller:
                    await interaction.edit_original_response(content="❌ Продавец не найден.")
                    return

                # Get the current embed from the message
                current_embed = interaction.message.embeds[0]

                # Check if the current embed is the trade embed or the profile embed
                if "Объявление об обмене" in current_embed.title:
                    # Currently showing trade embed, switch to profile embed
                    profile_embed = disnake.Embed(
                        title=f"👤 Профиль продавца: {seller.name}",
                        description=f"**ID продавца:** {seller.id}\n"
                                  f"**Дата регистрации:** <t:{int(seller.created_at.timestamp())}:R>\n"
                                  f"**Активных объявлений:** {len([t for t in self.cog.trading_data['trades'].values() if t['seller'] == str(seller.id) and t['status'] == 'active'])}",
                        color=disnake.Color.blue() # Use a different color for profile embed
                    )
                    profile_embed.set_thumbnail(url=seller.display_avatar.url)

                    # Edit the message with the profile embed
                    await interaction.message.edit(embed=profile_embed)

                    # Change the button label to indicate next action
                    button.label = "⬅️ К объявлению" # Add emoji
                    # Edit the view on the original message to update the button
                    await interaction.message.edit(view=self) # Edit the message with the updated view

                else:
                    # Currently showing profile embed, switch back to trade embed
                    # Recreate the original trade embed from stored data
                    original_embed_data = trade.get('original_embed')
                    if not original_embed_data:
                        await interaction.edit_original_response(content="❌ Не удалось загрузить данные оригинального объявления.")
                        return

                    original_embed = disnake.Embed.from_dict(original_embed_data)

                    # Edit the message with the original trade embed
                    await interaction.message.edit(embed=original_embed)

                    # Change the button label back
                    button.label = "👤 Профиль автора объявления" # Add emoji
                    # Edit the view on the original message to update the button
                    await interaction.message.edit(view=self)

        # Send the message with embed and view
        message = await target_channel.send(embed=embed, view=TradeButtons(self, trade_id)) # Pass trade_id here

        # Store the trade with message and channel info and original embed data
        trade['message_id'] = message.id
        trade['channel_id'] = target_channel.id
        trade['original_embed'] = embed.to_dict() # Store embed as dictionary
        self.trading_data['trades'][trade_id] = trade
        self.save_trading_data()

        await inter.edit_original_response(content="✅ Торговое предложение успешно создано!")

    async def cancel_trade_message(self, inter: disnake.ApplicationCommandInteraction, trade_id: str):
        if trade_id not in self.trading_data.get('trades', {}):
            await inter.edit_original_response(content="❌ Торговое предложение не найдено.")
            return

        trade = self.trading_data['trades'][trade_id]

        if str(inter.user.id) != trade['seller']:
            await inter.edit_original_response(content="❌ У вас нет прав для отмены этого торгового предложения!")
            return

        trade['status'] = 'cancelled'
        trade['cancelled_at'] = datetime.now().isoformat()
        self.save_trading_data()

        channel = self.bot.get_channel(trade['channel_id'])
        if channel:
            try:
                message = await channel.fetch_message(trade['message_id'])
                embed = message.embeds[0]
                embed.color = disnake.Color.red() # Red color for cancelled
                embed.title = f"❌ Отменено: {trade['item_name']}"
                # Add a field indicating cancellation time (optional)
                embed.add_field(
                    name="Статус",
                    value=f"Отменено <t:{int(datetime.fromisoformat(trade['cancelled_at']).timestamp())}:R>",
                    inline=False
                )
                await message.edit(embed=embed, view=None)
            except disnake.NotFound:
                print(f"Message with ID {trade['message_id']} not found for cancellation.")
            except Exception as e:
                print(f"Error editing message {trade['message_id']}: {e}")
        else:
            print(f"Channel with ID {trade['channel_id']} not found for cancellation.")

        await inter.edit_original_response(content="✅ Торговое предложение успешно отменено!")

    @commands.slash_command(
        name="tradelist",
        description="Показать активные торговые предложения"
    )
    async def list_trades(
        self,
        inter: disnake.ApplicationCommandInteraction,
        category: str = commands.Param(
            description="Фильтр по категории",
            choices=["Все", "👔 Костюмы", "💣 Оружие", "✨ Артефакты", "📏 Обвесы", "💊 Медицина", "⚒️ Крафт", "📦 Прочее"],
            default="Все"
        )
    ):
        await inter.response.defer()

        # Filter trades
        active_trades = [
            trade for trade in self.trading_data['trades'].values()
            if trade['status'] == 'active' and (category == "Все" or trade['category'] == category)
        ]

        if not active_trades:
            await inter.edit_original_response(content="📭 Активных торговых предложений не найдено!")
            return

        # Create embed with list of offers
        embed = disnake.Embed(
            title=f"🛍️ Активные торговые предложения{f' в категории: {category}' if category != 'Все' else ''}", # More descriptive title
            color=disnake.Color.blue()
        )

        # Group trades by category
        trades_by_category = {}
        for trade in active_trades:
            category = trade.get('category', '📦 Прочее')
            if category not in trades_by_category:
                trades_by_category[category] = []
            trades_by_category[category].append(trade)

        for category, trades in trades_by_category.items():
            trade_list_text = ""
            for trade in trades:
                seller = self.bot.get_user(int(trade['seller']))
                seller_name = seller.name if seller else "Неизвестный продавец"
                
                trade_list_text += f"**{trade['item_name']}** ({trade['price']} монет) 💰\n"
                trade_list_text += f"  👤 Продавец: {seller_name}\n"
                trade_list_text += f"  ⏰ Действует до: <t:{int(datetime.fromisoformat(trade['expires_at']).timestamp())}:R>\n"
                trade_list_text += f"  🔗 ID: `{trade['id']}`\n\n" # Format ID as code

            embed.add_field(
                name=f"__**{category}**__",
                value=trade_list_text if trade_list_text else "Нет активных предложений в этой категории.",
                inline=False
            )

        await inter.edit_original_response(embed=embed)

    @commands.slash_command(
        name="tradehistory",
        description="Показать историю торгов"
    )
    async def trade_history(
        self,
        inter: disnake.ApplicationCommandInteraction,
        user: disnake.Member = commands.Param(description="Пользователь (оставьте пустым для просмотра всей истории)", default=None)
    ):
        await inter.response.defer()

        # Filter trades
        completed_trades = [
            trade for trade in self.trading_data['trades'].values()
            if trade['status'] == 'completed' and (user is None or str(user.id) in [trade['seller'], trade.get('buyer')])
        ]

        if not completed_trades:
            await inter.edit_original_response(content="📭 История торгов пуста!")
            return

        # Create embed with history
        embed = disnake.Embed(
            title=f"📜 История торгов{f' пользователя: {user.name}' if user else ''}", # More descriptive title
            color=disnake.Color.blue()
        )

        # Group trades by category
        trades_by_category = {}
        for trade in completed_trades:
            category = trade.get('category', '📦 Прочее')
            if category not in trades_by_category:
                trades_by_category[category] = []
            trades_by_category[category].append(trade)

        for category, trades in trades_by_category.items():
            trade_list_text = ""
            for trade in trades:
                seller = self.bot.get_user(int(trade['seller']))
                buyer = self.bot.get_user(int(trade.get('buyer', 0)))
                
                seller_name = seller.name if seller else "Неизвестный продавец"
                buyer_name = buyer.name if buyer else "Неизвестный покупатель"
                
                trade_list_text += f"**{trade['item_name']}** ({trade['price']} монет) 💰\n"
                trade_list_text += f"  👤 Продавец: {seller_name}\n"
                trade_list_text += f"  👥 Покупатель: {buyer_name}\n"
                trade_list_text += f"  ✅ Завершено: <t:{int(datetime.fromisoformat(trade['completed_at']).timestamp())}:R>\n"
                trade_list_text += f"  🔗 ID: `{trade['id']}`\n\n" # Format ID as code

            embed.add_field(
                name=f"__**{category}**__",
                value=trade_list_text if trade_list_text else "Нет завершенных сделок в этой категории.",
                inline=False
            )

        await inter.edit_original_response(embed=embed)

    @commands.slash_command(
        name="marktradecompleted",
        description="Отметить торговое предложение как завершенное (только продавец)"
    )
    async def mark_trade_completed(
        self,
        inter: disnake.ApplicationCommandInteraction,
        trade_id: str = commands.Param(description="ID торгового предложения для отметки завершения")
    ):
        await inter.response.defer(ephemeral=True)

        # Find the trade by trade ID
        if trade_id not in self.trading_data.get('trades', {}):
            await inter.edit_original_response(content="❌ Торговое предложение не найдено.")
            return

        trade = self.trading_data['trades'][trade_id]

        # Check if the user is the seller
        if str(inter.user.id) != trade['seller']:
            await inter.edit_original_response(content="❌ У вас нет прав для завершения этого торгового предложения!")
            return

        # Check if the trade is already completed or cancelled
        if trade['status'] != 'active':
            await inter.edit_original_response(content=f"❌ Это торговое предложение уже {trade['status']}.")
            return

        # Update trade status to completed
        trade['status'] = 'completed'
        trade['completed_at'] = datetime.now().isoformat()
        self.save_trading_data()

        # Edit the message to indicate completion
        channel = self.bot.get_channel(trade['channel_id'])
        if channel:
            try:
                message = await channel.fetch_message(trade['message_id'])
                embed = message.embeds[0]
                embed.color = disnake.Color.green() # Use green for completed
                embed.title = f"✅ СДЕЛА ЗАВЕРШЕНА: {trade['item_name']}" # More prominent title
                # Add buyer to embed
                buyer_id = trade.get('buyer')
                if buyer_id:
                    # Check if field already exists to avoid duplicates on re-edits
                    buyer_field_exists = any(field.name == "👥 Покупатель:" for field in embed.fields)
                    if not buyer_field_exists:
                        embed.add_field(name="👥 Покупатель:", value=f"<@{buyer_id}>", inline=False) # Add emoji

                await message.edit(embed=embed, view=None) # Remove buttons
            except disnake.NotFound:
                print(f"Message with ID {trade['message_id']} not found for completion.")
            except Exception as e:
                 print(f"Error editing message {trade['message_id']}: {e}")
        else:
             print(f"Channel with ID {trade['channel_id']} not found for completion.")

        await inter.edit_original_response(content="✅ Торговое предложение успешно отмечено как завершенное!")

    @commands.slash_command(
        name="viewinterest",
        description="Показать список пользователей, заинтересованных в вашем торговом предложении (только продавец)"
    )
    async def view_interest(
        self,
        inter: disnake.ApplicationCommandInteraction,
        trade_id: str = commands.Param(description="ID торгового предложения")
    ):
        await inter.response.defer(ephemeral=True)

        # Find the trade
        trade = self.trading_data['trades'].get(trade_id)

        if not trade:
            await inter.edit_original_response(content="❌ Торговое предложение не найдено.")
            return

        # Check if the user is the seller
        if str(inter.user.id) != trade.get('seller'):
            await inter.edit_original_response(content="❌ У вас нет прав для просмотра заинтересованных пользователей этого предложения!")
            return

        # Get interested users
        interested_users_ids = trade.get('interested_users', [])

        if not interested_users_ids:
            await inter.edit_original_response(content="🤷‍♂️ Пока нет заинтересованных пользователей для этого предложения.")
            return

        # Fetch user objects and create a list for display
        user_mentions = []
        for user_id in interested_users_ids:
            user = self.bot.get_user(int(user_id))
            if user:
                user_mentions.append(f"• {user.mention}") # Use bullet point
            else:
                user_mentions.append(f"• Неизвестный пользователь (ID: {user_id})") # Use bullet point

        embed = disnake.Embed(
            title=f"👀 Заинтересованные пользователи для: {trade.get('item_name', 'Неизвестный предмет')}", # Changed emoji
            description="\n".join(user_mentions),
            color=disnake.Color.blue()
        )
        embed.set_footer(text=f"ID предложения: {trade_id}")

        await inter.edit_original_response(embed=embed)

    @commands.slash_command(
        name="manageinterest",
        description="Управлять пользователями, заинтересованными в вашем предложении (только продавец)"
    )
    async def manage_interest(
        self,
        inter: disnake.ApplicationCommandInteraction,
        trade_id: str = commands.Param(description="ID торгового предложения"),
        user: disnake.Member = commands.Param(description="Пользователь, чьим интересом вы управляете"),
        action: str = commands.Param(description="Действие", choices=["approve", "reject"])
    ):
        await inter.response.defer(ephemeral=True)

        # Find the trade
        trade = self.trading_data['trades'].get(trade_id)

        if not trade:
            await inter.edit_original_response(content="❌ Торговое предложение не найдено.")
            return

        # Check if the user is the seller
        if str(inter.user.id) != trade.get('seller'):
            await inter.edit_original_response(content="❌ У вас нет прав для управления заинтересованными пользователями этого предложения!")
            return

        # Get interested users IDs
        interested_users_ids = trade.get('interested_users', [])
        user_id_str = str(user.id)

        # Check if the target user is in the interested list
        if user_id_str not in interested_users_ids:
            await inter.edit_original_response(content=f"❌ Пользователь {user.mention} не проявил интерес к этому предложению.")
            return

        if action == "approve":
            # Approve the user - send contact info DMs
            seller = inter.user # Seller is the one using the command
            buyer = user       # Buyer is the user being approved

            try:
                # Send DM to buyer
                buyer_embed = disnake.Embed(
                    title=f"✅ Интерес одобрен! Приготовьтесь к сделке!",
                    description=f"Продавец {seller.mention} одобрил ваш интерес к предмету **{trade['item_name']}**!\n\n"
                              f"**💰 Цена:** {trade['price']} монет\n\n"
                              f"*Свяжитесь с продавцом {seller.mention} для завершения сделки.*",
                    color=disnake.Color.blue()
                )
                if trade.get('image_urls'):
                    buyer_embed.set_image(url=trade['image_urls'][0])
                buyer_embed.set_thumbnail(url=seller.display_avatar.url) # Add seller thumbnail
                await buyer.send(embed=buyer_embed)

                # Send DM to seller with buyer info
                seller_embed = disnake.Embed(
                    title=f"✅ Вы одобрили интерес пользователя!",
                    description=f"Вы одобрили интерес пользователя {buyer.mention} к вашему предмету **{trade['item_name']}**.\n\n"
                              f"**💰 Цена:** {trade['price']} монет\n\n"
                              f"*Свяжитесь с покупателем {buyer.mention} для завершения сделки.*",
                    color=disnake.Color.green()
                )
                if trade.get('image_urls'):
                    seller_embed.set_image(url=trade['image_urls'][0])
                seller_embed.set_thumbnail(url=buyer.display_avatar.url) # Add buyer thumbnail
                await seller.send(embed=seller_embed)

                # Optionally remove other interested users or mark this one as approved in data
                # For now, just remove all from the list after one is approved
                trade['interested_users'] = [] # Clear list after one approval
                trade['approved_buyer'] = user_id_str # Store the approved buyer
                self.save_trading_data()

                await inter.edit_original_response(content=f"✅ Интерес пользователя {user.mention} одобрен. Информация для связи отправлена в ЛС.")

            except disnake.Forbidden:
                 await inter.edit_original_response(content="❌ Не удалось отправить личные сообщения. Убедитесь, что у обоих пользователей разрешены ЛС от участников сервера.")
            except Exception as e:
                 print(f"Error sending approval DMs: {e}")
                 await inter.edit_original_response(content=f"❌ Произошла ошибка при отправке контактной информации: {e}")

        elif action == "reject":
            # Reject the user - remove from interested list
            trade['interested_users'].remove(user_id_str)
            self.save_trading_data()

            # Optionally notify the rejected user (via DM)
            try:
                # Format rejection notification as an embed
                rejection_embed = disnake.Embed(
                    title=f"❌ Интерес отклонен",
                    description=f"К сожалению, продавец отклонил ваш интерес к предложению:\n\n"
                               f"**🛍️ Предмет:** {trade['item_name']}\n"
                               f"**💰 Цена:** {trade['price']} монет\n\n"
                               f"*Вы больше не в списке заинтересованных пользователей для этого предложения.*",
                    color=disnake.Color.red()
                )
                if trade.get('image_urls'):
                    rejection_embed.set_image(url=trade['image_urls'][0])
                await user.send(embed=rejection_embed)

            except disnake.Forbidden:
                 print(f"Could not send rejection DM to user {user.id}.")

            await inter.edit_original_response(content=f"✅ Интерес пользователя {user.mention} отклонен и удален из списка.")

def setup(bot):
    cog = Trading(bot)
    bot.add_cog(cog)