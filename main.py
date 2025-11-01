# ==============================================================================
# main.py - Point d'entrée principal pour l'assistant de trading IA TradeGenie
# ==============================================================================

# Imports des bibliothèques standards
import os
import asyncio
import logging
import time
import re # Nouveau: pour l'analyse des commandes utilisateur
from functools import wraps # Pour les décorateurs de nettoyage

# Imports des bibliothèques tierces
import nest_asyncio # Pour la compatibilité Jupyter/IPython
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes,
    ConversationHandler,
    CallbackContext
)

# Appliquer nest_asyncio immédiatement pour la compatibilité Jupyter
nest_asyncio.apply()

# Imports locaux - Nos modules personnalisés
from config import (
    TELEGRAM_TOKEN,
    LOGGING_LEVEL,
    LOGGING_FORMAT,
    ALLOWED_UPDATES,
    MAX_IMAGE_SIZE_BYTES,
    SUPPORTED_ASSETS,
    SUPPORTED_MODULES,
    DEFAULT_RISK_PERCENT,
    ASSET_PIP_VALUES,
    # États de conversation
    GET_TRADE_PARAMS,
    WAITING_H4_IMAGE,
    WAITING_H1_IMAGE,
    WAITING_M15_IMAGE,
    # Chemins des prompts
    CHATGPT_SWING_VISION_PROMPT_PATH,
    CHATGPT_AMD_VISION_PROMPT_PATH,
    DEEPSEEK_SWING_PROMPT_PATH,
    DEEPSEEK_AMD_PROMPT_PATH,
    CHATGPT_MODEL,
    CHATGPT_BASE_SYSTEM_PROMPT_PATH,
    DEEPSEEK_MODEL,
    DEEPSEEK_BASE_SYSTEM_PROMPT_PATH,
    PROMPT_DIR,
    USER_DATA_CLEANUP_INTERVAL_SECONDS
)
from utils.image_processing import image_to_base64 # Pour l'encodage des images
from utils.risk_management import calculate_position_size # Pour le calcul de la taille de position
from utils.data_management import cleanup_old_user_data # Pour le nettoyage des données utilisateur
from llm_integrations.chatgpt_api import get_chatgpt_vision_analysis # Maintenant utilisé pour l'analyse vision
from llm_integrations.deepseek_api import get_deepseek_chat_completion # Utilisé pour la stratégie de trading

# --- 1. Configuration de la journalisation (Logging) ---
logging.basicConfig(
    format=LOGGING_FORMAT,
    level=LOGGING_LEVEL,
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

# --- 2. Gestion de l'état global de la conversation ---
# Ce dictionnaire stockera les données temporaires de l'utilisateur pendant un cycle de conversation.
# Clé: user_id (int) -> Valeur: dict (e.g., {'capital': 10000, 'asset': 'XAUUSD', 'module': 'SWING', ...})
user_conversation_data = {}

# --- Fonction utilitaire pour charger les prompts ---
def _load_prompt_from_file(file_path: str) -> str:
    """Charge une chaîne de prompt depuis un chemin de fichier donné."""
    full_path = os.path.join(os.getcwd(), file_path) # Utilise le chemin complet
    try:
        with open(full_path, 'r', encoding='utf-8') as f:
            return f.read().strip()
    except FileNotFoundError:
        logger.error(f"Fichier de prompt non trouvé: {full_path}")
        return ""
    except Exception as e:
        logger.error(f"Erreur lors du chargement du prompt depuis {full_path}: {e}")
        return ""

# --- Décorateur pour nettoyer les données utilisateur après une fonction ---
def clear_user_data_on_exit(func):
    """Décorateur pour supprimer les données utilisateur après l'exécution d'une fonction."""
    @wraps(func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        user_id = update.effective_user.id
        try:
            return await func(update, context, *args, **kwargs)
        finally:
            if user_id in user_conversation_data:
                del user_conversation_data[user_id]
                logger.info(f"Données utilisateur {user_id} effacées après l'exécution de {func.__name__}.")
    return wrapper

# --- Tâche de nettoyage planifiée ---
async def scheduled_cleanup(context: ContextTypes.DEFAULT_TYPE):
    """Tâche périodique pour nettoyer les anciennes données de conversation."""
    cleanup_old_user_data(user_conversation_data)


# ==============================================================================
# Fonctions de gestionnaire Telegram
# ==============================================================================

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Envoie un message de bienvenue lorsque la commande /start est émise."""
    user = update.effective_user
    await update.message.reply_html(
        f"Salut {user.mention_html()}! Je suis TradeGenie, votre assistant de trading IA.\n\n"
        "Je peux vous aider à analyser des graphiques et générer des plans de trading.\n"
        "Utilisez /analyze pour commencer une nouvelle analyse.\n"
        "Pour plus d'aide, utilisez /help."
    )
    logger.info(f"Utilisateur {user.id} ({user.first_name}) a démarré le bot.")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Envoie un message d'aide lorsque la commande /help est émise."""
    help_text = """
📚 **GUIDE D'UTILISATION DE TRADEGENIE**

🚀 **Pour commencer une analyse:**
1. Tapez `/analyze`
2. Envoyez la commande de paramètres de trading :
   `/trade [ASSET] [MODULE] [CAPITAL]`
   Ex: `/trade XAUUSD SWING 100000`
   (Assets supportés: XAUUSD, EURUSD; Modules supportés: SWING, AMD)
3. Envoyez le graphique **H4** (cadre 4 heures) comme photo.
4. Envoyez le graphique **H1** (cadre 1 heure) comme photo.
5. (Pour le module AMD uniquement) Envoyez le graphique **M15** (cadre 15 minutes) comme photo.
6. Recevez votre analyse complète et votre plan de trading!

⚡ **Autres commandes:**
• `/status` - Voir l'état actuel du bot.
• `/cancel` - Annuler l'analyse en cours et effacer les données.

📊 **Comprendre votre analyse:**
- **SWING:** Analyse de tendance H4/H1 pour le trading de swing.
- **AMD:** Analyse d'Accumulation, Manipulation, Distribution H4/M15.

⚠️ **Disclaimer:** L'analyse est générée par IA. Effectuez toujours vos propres recherches et gestion des risques.
"""
    await update.message.reply_text(help_text, parse_mode='Markdown')
    logger.info(f"Utilisateur {update.effective_user.id} a demandé de l'aide.")

async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Affiche le statut du bot et des utilisateurs actifs."""
    # Nettoyer les données avant d'afficher le statut
    cleanup_old_user_data(user_conversation_data)
    
    status_msg = (
        "🤖 **STATUS TRADEGENIE**\n\n"
        f"• 👥 Utilisateurs actifs en conversation: {len(user_conversation_data)}\n"
        f"• ⏰ Heure actuelle: {time.strftime('%H:%M:%S')}\n\n"
        "**Services LLM (vérifiés par leur clé API):**\n"
        f"• ChatGPT: {'✅ Disponible' if OPENAI_API_KEY else '❌ Clé manquante'}\n"
        f"• DeepSeek: {'✅ Disponible' if DEEPSEEK_API_KEY else '❌ Clé manquante'}\n"
        # Ajoutez le statut de Claude si vous le souhaitez, basé sur CLAUDE_API_KEY par exemple
    )
    await update.message.reply_text(status_msg, parse_mode='Markdown')
    logger.info(f"Utilisateur {update.effective_user.id} a demandé le statut.")

@clear_user_data_on_exit # Le décorateur s'assurera du nettoyage
async def cancel_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Annule et termine la conversation."""
    await update.message.reply_text(
        "❌ **Analyse annulée.** Toutes les données de cette session ont été effacées.\n"
        "Pour recommencer, tapez /analyze.",
        parse_mode='Markdown'
    )
    logger.info(f"Utilisateur {update.effective_user.id} a annulé la conversation.")
    return ConversationHandler.END


# ==============================================================================
# Fonctions du gestionnaire de conversation (Trading Analysis Flow)
# ==============================================================================

async def analyze_entry_point(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Démarre une nouvelle analyse de trading."""
    user_id = update.effective_user.id
    user_conversation_data[user_id] = {'timestamp': time.time()} # Initialise les données utilisateur
    await update.message.reply_text(
        "🚀 **Nouvelle analyse de trading démarrée!**\n"
        "Veuillez maintenant spécifier les paramètres:\n"
        "Ex: `/trade XAUUSD SWING 100000`\n\n"
        f"Assets supportés: {', '.join(SUPPORTED_ASSETS)}\n"
        f"Modules supportés: {', '.join(SUPPORTED_MODULES)}",
        parse_mode='Markdown'
    )
    logger.info(f"Utilisateur {user_id} a démarré le processus /analyze.")
    return GET_TRADE_PARAMS

async def get_trade_parameters(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Reçoit et valide les paramètres de trade (asset, module, capital)."""
    user_id = update.effective_user.id
    message_text = update.message.text

    # Regex pour parser la commande: /trade [ASSET] [MODULE] [CAPITAL]
    match = re.match(r'/trade\s+([A-Za-z0-9]+)\s+([A-Za-z]+)\s+([\d,\.]+)', message_text)

    if not match:
        await update.message.reply_text(
            "❌ Format de commande invalide. Utilisez: `/trade [ASSET] [MODULE] [CAPITAL]`\n"
            "Ex: `/trade XAUUSD SWING 100000`",
            parse_mode='Markdown'
        )
        return GET_TRADE_PARAMS

    asset = match.group(1).upper()
    module = match.group(2).upper()
    capital_str = match.group(3).replace(',', '.') # Gérer les virgules comme séparateur décimal

    try:
        capital = float(capital_str)
    except ValueError:
        await update.message.reply_text("❌ Capital invalide. Veuillez entrer un nombre valide (ex: 100000 ou 5000.50).")
        return GET_TRADE_PARAMS
    
    if asset not in SUPPORTED_ASSETS:
        await update.message.reply_text(f"❌ Asset '{asset}' non supporté. Supportés: {', '.join(SUPPORTED_ASSETS)}.")
        return GET_TRADE_PARAMS

    if module not in SUPPORTED_MODULES:
        await update.message.reply_text(f"❌ Module '{module}' non supporté. Supportés: {', '.join(SUPPORTED_MODULES)}.")
        return GET_TRADE_PARAMS

    if capital <= 0:
        await update.message.reply_text("❌ Le capital de trading doit être un nombre positif.")
        return GET_TRADE_PARAMS

    user_conversation_data[user_id]['asset'] = asset
    user_conversation_data[user_id]['module'] = module
    user_conversation_data[user_id]['capital'] = capital
    user_conversation_data[user_id]['timestamp'] = time.time() # Met à jour le timestamp d'activité

    await update.message.reply_text(
        f"✅ Paramètres enregistrés:\n"
        f"Asset: **{asset}**\nModule: **{module}**\nCapital: **${capital:,.2f}**\n\n"
        "Veuillez maintenant envoyer le graphique **H4** (cadre 4 heures) comme une photo.",
        parse_mode='Markdown'
    )
    logger.info(f"Utilisateur {user_id}: Paramètres reçus (Asset: {asset}, Module: {module}, Capital: {capital}).")
    return WAITING_H4_IMAGE


async def receive_h4_image(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Reçoit l'image H4 et demande l'image H1."""
    user_id = update.effective_user.id
    
    if not update.message.photo:
        await update.message.reply_text("❌ Veuillez envoyer une *photo* pour le graphique H4.")
        return WAITING_H4_IMAGE # Reste dans le même état

    if user_id not in user_conversation_data:
        await update.message.reply_text("❌ Session expirée ou données manquantes. Veuillez recommencer avec /analyze.", parse_mode='Markdown')
        return ConversationHandler.END

    file_id = update.message.photo[-1].file_id # Obtient l'image de la plus haute résolution
    file = await context.bot.get_file(file_id)
    
    if file.file_size > MAX_IMAGE_SIZE_BYTES:
        await update.message.reply_text(f"❌ L'image H4 est trop volumineuse ({file.file_size / (1024*1024):.1f}MB). Maximum: {MAX_IMAGE_SIZE_BYTES / (1024*1024):.1f}MB.")
        return WAITING_H4_IMAGE
    
    image_bytes = BytesIO()
    await file.download_to_memory(image_bytes)
    user_conversation_data[user_id]['h4_image'] = image_bytes.getvalue()
    user_conversation_data[user_id]['timestamp'] = time.time()

    logger.info(f"Utilisateur {user_id}: Image H4 reçue.")
    await update.message.reply_text(
        "✅ H4 reçu. Veuillez maintenant envoyer le graphique **H1** (cadre 1 heure) comme une photo.",
        parse_mode='Markdown'
    )
    return WAITING_H1_IMAGE


async def receive_h1_image(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Reçoit l'image H1 et, si nécessaire, demande l'image M15 ou lance l'analyse."""
    user_id = update.effective_user.id

    if not update.message.photo:
        await update.message.reply_text("❌ Veuillez envoyer une *photo* pour le graphique H1.")
        return WAITING_H1_IMAGE

    if user_id not in user_conversation_data:
        await update.message.reply_text("❌ Session expirée ou données manquantes. Veuillez recommencer avec /analyze.", parse_mode='Markdown')
        return ConversationHandler.END
    
    file_id = update.message.photo[-1].file_id
    file = await context.bot.get_file(file_id)

    if file.file_size > MAX_IMAGE_SIZE_BYTES:
        await update.message.reply_text(f"❌ L'image H1 est trop volumineuse ({file.file_size / (1024*1024):.1f}MB). Maximum: {MAX_IMAGE_SIZE_BYTES / (1024*1024):.1f}MB.")
        return WAITING_H1_IMAGE

    image_bytes = BytesIO()
    await file.download_to_memory(image_bytes)
    user_conversation_data[user_id]['h1_image'] = image_bytes.getvalue()
    user_conversation_data[user_id]['timestamp'] = time.time()

    logger.info(f"Utilisateur {user_id}: Image H1 reçue.")

    if user_conversation_data[user_id]['module'] == "AMD":
        await update.message.reply_text(
            "✅ H1 reçu. Puisque le module **AMD** a été choisi, veuillez maintenant envoyer le graphique **M15** (cadre 15 minutes) comme une photo.",
            parse_mode='Markdown'
        )
        return WAITING_M15_IMAGE
    else: # SWING module ou tout autre module ne nécessitant pas M15
        return await start_llm_analysis(update, context)


@clear_user_data_on_exit # Le décorateur s'assurera du nettoyage
async def receive_m15_image(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Reçoit l'image M15 (pour AMD) et lance l'analyse LLM."""
    user_id = update.effective_user.id

    if not update.message.photo:
        await update.message.reply_text("❌ Veuillez envoyer une *photo* pour le graphique M15.")
        return WAITING_M15_IMAGE

    if user_id not in user_conversation_data:
        await update.message.reply_text("❌ Session expirée ou données manquantes. Veuillez recommencer avec /analyze.", parse_mode='Markdown')
        return ConversationHandler.END

    file_id = update.message.photo[-1].file_id
    file = await context.bot.get_file(file_id)

    if file.file_size > MAX_IMAGE_SIZE_BYTES:
        await update.message.reply_text(f"❌ L'image M15 est trop volumineuse ({file.file_size / (1024*1024):.1f}MB). Maximum: {MAX_IMAGE_SIZE_BYTES / (1024*1024):.1f}MB.")
        return WAITING_M15_IMAGE

    image_bytes = BytesIO()
    await file.download_to_memory(image_bytes)
    user_conversation_data[user_id]['m15_image'] = image_bytes.getvalue()
    user_conversation_data[user_id]['timestamp'] = time.time()

    logger.info(f"Utilisateur {user_id}: Image M15 reçue.")
    return await start_llm_analysis(update, context)


@clear_user_data_on_exit # Le décorateur s'assurera du nettoyage
async def start_llm_analysis(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Lance l'analyse des LLM en utilisant les images et paramètres collectés."""
    user_id = update.effective_user.id
    user_data = user_conversation_data.get(user_id) # On l'appelle user_data localement

    if not user_data: # Double vérification, si le décorateur ne suffit pas
        await update.message.reply_text("❌ Session expirée ou données manquantes. Veuillez recommencer avec /analyze.", parse_mode='Markdown')
        return ConversationHandler.END

    await update.message.reply_text(
        "⏳ **Analyse en cours...**\n\n"
        "• ChatGPT: Analyse technique visuelle 📊\n"
        "• DeepSeek: Élaboration de la stratégie de trading 💡\n"
        "• Patience requise, cela peut prendre 30 à 60 secondes...",
        parse_mode='Markdown'
    )
    logger.info(f"Utilisateur {user_id}: Démarrage de l'analyse LLM pour le module {user_data['module']}.")

    capital = user_data['capital']
    asset = user_data['asset']
    module = user_data['module']
    h4_image = user_data.get('h4_image')
    h1_image = user_data.get('h1_image')
    m15_image = user_data.get('m15_image')


    # --- 1. Préparation pour l'analyse ChatGPT Vision ---
    chatgpt_vision_user_prompt = ""
    images_to_send_to_chatgpt = []

    if module == "SWING":
        chatgpt_vision_user_prompt = _load_prompt_from_file(CHATGPT_SWING_VISION_PROMPT_PATH)
        images_to_send_to_chatgpt = [h4_image, h1_image]
    elif module == "AMD":
        chatgpt_vision_user_prompt = _load_prompt_from_file(CHATGPT_AMD_VISION_PROMPT_PATH)
        # Pour AMD, nous envoyons H4 et M15
        images_to_send_to_chatgpt = [h4_image, m15_image]
    
    if not chatgpt_vision_user_prompt:
        await update.message.reply_text("❌ Erreur: Prompt Vision pour ChatGPT introuvable pour ce module.")
        return ConversationHandler.END
    if not all(images_to_send_to_chatgpt): # Vérifie si toutes les images nécessaires sont là
        await update.message.reply_text("❌ Erreur: Images requises (H4/H1 ou H4/M15) manquantes pour l'analyse vision.")
        return ConversationHandler.END
    
    # --- Appel à ChatGPT Vision ---
    chatgpt_analysis_text = await get_chatgpt_vision_analysis(
        user_prompt=chatgpt_vision_user_prompt,
        image_bytes_list=images_to_send_to_chatgpt,
        system_prompt=_load_prompt_from_file(CHATGPT_BASE_SYSTEM_PROMPT_PATH),
        model=CHATGPT_MODEL
    )
    logger.info(f"Utilisateur {user_id}: Analyse ChatGPT Vision terminée.")

    # Vérifier si ChatGPT a retourné une erreur
    if chatgpt_analysis_text.startswith("❌"):
        await update.message.reply_text(f"❌ Erreur lors de l'analyse Vision par ChatGPT: {chatgpt_analysis_text}\n"
                                        "Veuillez réessayer ou contacter le support.", parse_mode='Markdown')
        return ConversationHandler.END


    # --- 2. Préparation et appel à DeepSeek pour la stratégie ---
    deepseek_strategy_prompt_template = ""
    if module == "SWING":
        deepseek_strategy_prompt_template = _load_prompt_from_file(DEEPSEEK_SWING_PROMPT_PATH)
    elif module == "AMD":
        deepseek_strategy_prompt_template = _load_prompt_from_file(DEEPSEEK_AMD_PROMPT_PATH)
    
    if not deepseek_strategy_prompt_template:
        await update.message.reply_text("❌ Erreur: Prompt de stratégie pour DeepSeek introuvable pour ce module.")
        return ConversationHandler.END

    # Calculer la taille de position initiale pour le prompt DeepSeek
    # DeepSeek n'a pas besoin de la taille finale mais des chiffres pour construire le plan
    # Nous pourrions prendre une SL 'générique' et laisser DeepSeek affiner, ou la laisser vide.
    # Pour l'instant, on laisse DeepSeek suggérer un SL et on le calcule après si besoin.
    # On passe le capital, le risque %
    
    # Formatter le prompt DeepSeek avec l'analyse de ChatGPT et les données utilisateur
    deepseek_formatted_prompt = deepseek_strategy_prompt_template.format(
        analysis_from_chatgpt=chatgpt_analysis_text, # Renommé pour être plus générique suite à l'absence de Claude
        asset_symbol=asset,
        capital=f"{capital:,.0f}", # Formatté pour le prompt
        risk_percent=f"{DEFAULT_RISK_PERCENT:.1f}", # Le prompt DeepSeek doit utiliser cette variable
        risk_amount="?", # DeepSeek calculera cela basé sur son SL suggéré ou nous le ferons après
        position_size_lots="?", # DeepSeek calculera cela basé sur son SL suggéré
        stop_loss_pips="?" # DeepSeek suggérera ceci
    )

    deepseek_trading_plan = await get_deepseek_chat_completion(
        user_prompt=deepseek_formatted_prompt,
        system_prompt=_load_prompt_from_file(DEEPSEEK_BASE_SYSTEM_PROMPT_PATH),
        model=DEEPSEEK_MODEL
    )
    logger.info(f"Utilisateur {user_id}: Plan de trading DeepSeek terminé.")

    # Vérifier si DeepSeek a retourné une erreur
    if deepseek_trading_plan.startswith("❌"):
        await update.message.reply_text(f"❌ Erreur lors de l'élaboration du plan de trading par DeepSeek: {deepseek_trading_plan}\n"
                                        "Veuillez réessayer ou contacter le support.", parse_mode='Markdown')
        return ConversationHandler.END

    # --- 3. Construction et envoi du message final à l'utilisateur ---
    final_message_parts = [
        f"🎯 **ANALYSE COMPLÈTE & PLAN DE TRADING AI ({module})**",
        f"💰 **Capital Trading:** ${capital:,.2f} | Asset: **{asset}**",
        "\n--- **Analyse Technique (par ChatGPT)** ---\n",
        chatgpt_analysis_text,
        "\n--- **Plan de Trading (par DeepSeek)** ---\n",
        deepseek_trading_plan,
        "\n⚠️ **AVERTISSEMENT:** Ceci est une analyse générée par une intelligence artificielle. "
        "Elle ne constitue en aucun cas un conseil financier. Effectuez toujours vos propres recherches, "
        "analyses et gestion des risques avant de prendre toute décision de trading. Le trading comporte des risques.",
    ]
    final_message = "\n".join(final_message_parts)

    # Gérer les messages longs (Telegram limite à 4096 caractères)
    if len(final_message) > 4000:
        # Tenter de couper intelligemment le message, par exemple à la fin de l'analyse technique
        # et commencer le plan de trading dans un nouveau message
        split_point = final_message.find("--- **Plan de Trading (par DeepSeek)** ---")
        if split_point != -1 and split_point < 3500: # Assure que la première partie est assez grande
            part1 = final_message[:split_point].strip() + "\n\n(Suite de l'analyse ci-dessous...)"
            part2 = final_message[split_point:].strip()

            await update.message.reply_text(part1, parse_mode='Markdown')
            await update.message.reply_text(part2, parse_mode='Markdown')
        else:
            # Si pas de split intelligent possible, juste couper par longueur brute
            for i in range(0, len(final_message), 4000):
                await update.message.reply_text(final_message[i:i+4000], parse_mode='Markdown')
    else:
        await update.message.reply_text(final_message, parse_mode='Markdown')

    logger.info(f"Utilisateur {user_id}: Analyse terminée et envoyée.")
    return ConversationHandler.END


# ==============================================================================
# Configuration principale du bot et exécution
# ==============================================================================

def main() -> None:
    """Démarre le bot."""
    if not TELEGRAM_TOKEN:
        logger.error("TELEGRAM_TOKEN n'est pas défini. Veuillez le définir dans config.py ou comme variable d'environnement.")
        return

    application = Application.builder().token(TELEGRAM_TOKEN).allowed_updates(ALLOWED_UPDATES).build()

    # --- Configuration du ConversationHandler ---
    trade_analysis_conversation_handler = ConversationHandler(
        entry_points=[CommandHandler("analyze", analyze_entry_point)],
        states={
            GET_TRADE_PARAMS: [MessageHandler(filters.COMMAND('trade') & filters.TEXT & ~filters.ChatType.CHANNEL, get_trade_parameters)],
            WAITING_H4_IMAGE: [MessageHandler(filters.PHOTO & ~filters.ChatType.CHANNEL, receive_h4_image)],
            WAITING_H1_IMAGE: [MessageHandler(filters.PHOTO & ~filters.ChatType.CHANNEL, receive_h1_image)],
            WAITING_M15_IMAGE: [MessageHandler(filters.PHOTO & ~filters.ChatType.CHANNEL, receive_m15_image)],
        },
        fallbacks=[CommandHandler("cancel", cancel_command)],
        allow_reentry=True # Permet aux utilisateurs de redémarrer avec /analyze n'importe quand
    )

    # --- Ajout des gestionnaires de commandes régulières ---
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("status", status_command))
    application.add_handler(CommandHandler("cancel", cancel_command)) # Un global /cancel

    # --- Ajout du gestionnaire de conversation ---
    application.add_handler(trade_analysis_conversation_handler)

    # --- Planifier la tâche de nettoyage ---
    application.job_queue.run_repeating(scheduled_cleanup, interval=USER_DATA_CLEANUP_INTERVAL_SECONDS, first=10) # Nettoyage après 10s, puis toutes les heures

    logger.info("Bot TradeGenie démarré (polling)...")
    application.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()