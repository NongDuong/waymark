SUPPORTED_LANGUAGES = {"de", "en", "es", "fr", "hi", "id", "it", "ja", "ko", "pt", "vi"}
DEFAULT_LANGUAGE = "en"


_TRANSLATIONS = {
    "en": {
        "titles": {1: "New like", 2: "New comment", 3: "New follower", 4: "New message"},
        "messages": {
            1: "{sender} liked your memory.",
            2: "{sender} commented on your memory.",
            3: "{sender} started following you.",
            4: "{sender} sent you a message.",
        },
    },
    "vi": {
        "titles": {1: "Lượt thích mới", 2: "Bình luận mới", 3: "Người theo dõi mới", 4: "Tin nhắn mới"},
        "messages": {
            1: "{sender} đã thích kỷ niệm của bạn.",
            2: "{sender} đã bình luận về kỷ niệm của bạn.",
            3: "{sender} đã bắt đầu theo dõi bạn.",
            4: "{sender} đã gửi cho bạn một tin nhắn.",
        },
    },
    "de": {
        "titles": {1: "Neues „Gefällt mir“", 2: "Neuer Kommentar", 3: "Neuer Follower", 4: "Neue Nachricht"},
        "messages": {
            1: "{sender} gefällt deine Erinnerung.",
            2: "{sender} hat deine Erinnerung kommentiert.",
            3: "{sender} folgt dir jetzt.",
            4: "{sender} hat dir eine Nachricht gesendet.",
        },
    },
    "es": {
        "titles": {1: "Nuevo Me gusta", 2: "Nuevo comentario", 3: "Nuevo seguidor", 4: "Nuevo mensaje"},
        "messages": {
            1: "A {sender} le gustó tu recuerdo.",
            2: "{sender} comentó tu recuerdo.",
            3: "{sender} comenzó a seguirte.",
            4: "{sender} te envió un mensaje.",
        },
    },
    "fr": {
        "titles": {1: "Nouveau J’aime", 2: "Nouveau commentaire", 3: "Nouvel abonné", 4: "Nouveau message"},
        "messages": {
            1: "{sender} a aimé votre souvenir.",
            2: "{sender} a commenté votre souvenir.",
            3: "{sender} a commencé à vous suivre.",
            4: "{sender} vous a envoyé un message.",
        },
    },
    "hi": {
        "titles": {1: "नई पसंद", 2: "नई टिप्पणी", 3: "नया फ़ॉलोअर", 4: "नया संदेश"},
        "messages": {
            1: "{sender} ने आपकी याद को पसंद किया।",
            2: "{sender} ने आपकी याद पर टिप्पणी की।",
            3: "{sender} ने आपको फ़ॉलो करना शुरू किया।",
            4: "{sender} ने आपको एक संदेश भेजा।",
        },
    },
    "id": {
        "titles": {1: "Suka baru", 2: "Komentar baru", 3: "Pengikut baru", 4: "Pesan baru"},
        "messages": {
            1: "{sender} menyukai kenangan Anda.",
            2: "{sender} mengomentari kenangan Anda.",
            3: "{sender} mulai mengikuti Anda.",
            4: "{sender} mengirimi Anda pesan.",
        },
    },
    "it": {
        "titles": {1: "Nuovo Mi piace", 2: "Nuovo commento", 3: "Nuovo follower", 4: "Nuovo messaggio"},
        "messages": {
            1: "A {sender} piace il tuo ricordo.",
            2: "{sender} ha commentato il tuo ricordo.",
            3: "{sender} ha iniziato a seguirti.",
            4: "{sender} ti ha inviato un messaggio.",
        },
    },
    "ja": {
        "titles": {1: "新しい「いいね」", 2: "新しいコメント", 3: "新しいフォロワー", 4: "新しいメッセージ"},
        "messages": {
            1: "{sender}さんがあなたの思い出に「いいね」しました。",
            2: "{sender}さんがあなたの思い出にコメントしました。",
            3: "{sender}さんがあなたをフォローしました。",
            4: "{sender}さんがあなたにメッセージを送信しました。",
        },
    },
    "ko": {
        "titles": {1: "새 좋아요", 2: "새 댓글", 3: "새 팔로워", 4: "새 메시지"},
        "messages": {
            1: "{sender}님이 회원님의 추억을 좋아합니다.",
            2: "{sender}님이 회원님의 추억에 댓글을 남겼습니다.",
            3: "{sender}님이 회원님을 팔로우하기 시작했습니다.",
            4: "{sender}님이 메시지를 보냈습니다.",
        },
    },
    "pt": {
        "titles": {1: "Nova curtida", 2: "Novo comentário", 3: "Novo seguidor", 4: "Nova mensagem"},
        "messages": {
            1: "{sender} curtiu sua memória.",
            2: "{sender} comentou na sua memória.",
            3: "{sender} começou a seguir você.",
            4: "{sender} enviou uma mensagem para você.",
        },
    },
}


def normalize_language_code(language_code: str | None) -> str:
    return (language_code or DEFAULT_LANGUAGE).strip().lower()


def notification_language(language_code: str | None) -> str:
    normalized = normalize_language_code(language_code)
    return normalized if normalized in SUPPORTED_LANGUAGES else DEFAULT_LANGUAGE


def localize_notification(language_code: str | None, notification_type: int, sender_name: str) -> tuple[str, str]:
    language = notification_language(language_code)
    translations = _TRANSLATIONS[language]
    title = translations["titles"].get(notification_type, "New notification")
    template = translations["messages"].get(notification_type, "{sender} sent you a notification.")
    return title, template.format(sender=sender_name)
