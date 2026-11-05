"""События игры. Добавляй новые сюда и в список EVENTS в конце файла."""
from __future__ import annotations

import random

from game.engine import apply_effects, by_mood, named, shift_loyalty, weakest
from game.models import Choice, Cult, Event

# ── Проповедь (базовое событие, доступно всегда) ─────────────────────────────

sermon = Event(
    id="sermon",
    weight=3,
    text=lambda c: by_mood(
        c,
        "Утро. Паства собралась у алтаря и смотрит на тебя с надеждой. "
        "Или просто ждёт завтрака — не разберёшь.",
        "Утро. Паства молча собралась у алтаря. Лица усталые, взгляды тяжёлые. "
        "Все ждут, что ты скажешь.",
    ),
    choices=[
        Choice(
            "Произнести пламенную проповедь о Великом Пробуждении",
            {"faith": 8, "stability": -3},
            lambda c: by_mood(
                c,
                "Ты так вдохновенно размахивал руками, что кто-то заплакал, "
                "а кто-то записал слова в блокнот. Вера крепнет, горло садится.",
                "Твой голос гремел под сводами. Одни зажглись, другие отвели глаза. "
                "Не всем по душе, когда говорят так громко.",
            ),
        ),
        Choice(
            "Провести тихую беседу о терпении и взаимопомощи",
            {"faith": 3, "stability": 4},
            "Никаких чудес, но люди разошлись спокойнее, чем пришли.",
        ),
        Choice(
            "Отменить службу: все слишком устали",
            {"stability": 2, "faith": -2},
            "Паства оценила передышку. Алтарь оценил меньше.",
        ),
    ],
)

# ── Голод ────────────────────────────────────────────────────────────────────

hunger = Event(
    id="hunger",
    weight=5,
    condition=lambda c: c.food <= 8,
    text=lambda c: by_mood(
        c,
        "Кто-то заглянул в кладовую и вернулся с видом человека, увидевшего призрак. "
        "Призрак оказался пустой бочкой.",
        "Кладовая почти пуста. Дети перестали шутить. Взрослые перестали "
        "делать вид, что всё в порядке.",
    ),
    choices=[
        Choice(
            "Объявить священный пост",
            {"faith": 6, "stability": -4, "food": 2},
            "«Голод очищает дух», — сказал ты. Желудки выразили несогласие, "
            "но вслух возразить никто не решился.",
        ),
        Choice(
            "Отправить паству собирать пищу",
            {"food": 10, "faith": -3, "stability": 2},
            "Принесли грибы, коренья и одну очень злую курицу. Жить можно.",
        ),
        Choice(
            "Принести в жертву священную козу",
            {"food": 12, "faith": -8, "stability": -2},
            lambda c: by_mood(
                c,
                "Коза приняла судьбу с достоинством. Рагу вышло превосходным, "
                "что только усилило чувство вины.",
                "Коза была последним символом, который у вас оставался. Ели молча.",
            ),
        ),
    ],
)

# ── Сомневающийся (личное событие: герой — самый неуверенный последователь) ──


def _doubter_subject(c: Cult):
    if len(c.followers) < 2:
        return None
    f = weakest(c)
    return f if f.loyalty < 50 else None


def _doubter_text(c: Cult) -> str:
    f = c.subject
    return by_mood(
        c,
        f"{f.name} ({f.traits[0]}) всё чаще задаёт неудобные вопросы. "
        "Вчера спросил, почему Великий Пробуждённый выглядит так, будто плохо спал.",
        f"{f.name} ({f.traits[0]}) шепчется по углам. Говорят, он больше не верит "
        "и уже подбирает себе слушателей.",
    )


def _talk(c: Cult, rng: random.Random) -> None:
    shift_loyalty(c.subject, +15)


def _denounce(c: Cult, rng: random.Random) -> None:
    shift_loyalty(c.subject, -20)


def _exile(c: Cult, rng: random.Random) -> None:
    c.followers.remove(c.subject)


doubter = Event(
    id="doubter",
    weight=3,
    subject=_doubter_subject,
    text=_doubter_text,
    choices=[
        Choice(
            "Поговорить с ним наедине",
            {"stability": 2},
            "Разговор вышел долгим. Сомнения не исчезли, но острые углы сгладились.",
            action=_talk,
        ),
        Choice(
            "Публично осудить маловера",
            {"faith": 6, "stability": -8},
            "Толпа одобрительно загудела. Только тихие лица в задних рядах "
            "запомнили, чем кончаются вопросы.",
            action=_denounce,
        ),
        Choice(
            "Изгнать из культа",
            {"stability": -3, "faith": 2},
            "Ворота закрылись. Паства поняла: сомнения здесь стоят дорого.",
            action=_exile,
        ),
    ],
)

# ── Паломники ────────────────────────────────────────────────────────────────

newcomers = Event(
    id="newcomers",
    weight=2,
    condition=lambda c: c.faith >= 45,
    text=lambda c: by_mood(
        c,
        "У ворот собрались паломники. Кто-то услышал о вашем культе. "
        "Кто-то просто пришёл, потому что у вас, говорят, бесплатный суп.",
        "У ворот стоят чужаки. Они выглядят голодными, и непонятно, "
        "чего они ищут: веры или крыши над головой.",
    ),
    choices=[
        Choice(
            "Принять всех",
            {"followers": 2, "food": -4, "stability": -2},
            "Двери открылись. Стало шумнее, теснее и заметно меньше еды.",
        ),
        Choice(
            "Принять после испытания",
            {"followers": 1, "faith": 2},
            "Испытание: три часа слушать твою проповедь. Один сбежал, "
            "второй остался и заплакал.",
        ),
        Choice(
            "Прогнать",
            {"stability": 2, "faith": -3},
            "Ворота остались закрытыми. Тише стало. Светлее — нет.",
        ),
    ],
)

# ── Соперник ─────────────────────────────────────────────────────────────────


def _debate(c: Cult, rng: random.Random) -> None:
    won = rng.random() < 0.5
    c.flags.add("debate_won" if won else "debate_lost")
    apply_effects(c, {"faith": 12 if won else -12}, rng)


rival = Event(
    id="rival",
    weight=3,
    once=True,
    condition=lambda c: c.day >= 4 and c.faith >= 40,
    text="Бродячий проповедник разбил лагерь у вашей деревни. Он утверждает, "
         "что знает Истину, и берёт за неё меньше.",
    choices=[
        Choice(
            "Вызвать на публичный диспут",
            {},
            lambda c: (
                "Ты разбил его доводы в пух. Толпа аплодировала, проповедник "
                "уехал, оставив после себя лишь сломанную тележку."
                if "debate_won" in c.flags
                else "Он оказался красноречивее. Часть паствы уехала с ним "
                     "«послушать ещё немного»."
            ),
            action=_debate,
        ),
        Choice(
            "Игнорировать",
            {"faith": -3, "stability": 1},
            "Проповедник уехал сам, но пара человек успела заглянуть к нему на огонёк.",
        ),
        Choice(
            "Подстроить ему «несчастный случай»",
            {"faith": 5, "stability": -6},
            "Тележка сама виновата. Паства делает вид, что ничего не слышала. "
            "Это тоже форма веры.",
        ),
    ],
)

# ── Чудо ─────────────────────────────────────────────────────────────────────


def _fake_miracle(c: Cult, rng: random.Random) -> None:
    c.flags.add("fake_miracle")


miracle = Event(
    id="miracle",
    weight=3,
    once=True,
    condition=lambda c: c.faith >= 70,
    text="Вера паствы так сильна, что люди готовы увидеть чудо в чём угодно. "
         "В том числе в том, чего нет.",
    choices=[
        Choice(
            "Устроить «чудо» (зеркала, дым и вовремя убранная лестница)",
            {"faith": 12},
            "Толпа рухнула на колени. Ты старался не смотреть на человека "
            "за алтарём с зеркалом.",
            action=_fake_miracle,
        ),
        Choice(
            "Честно признать: чудес не обещано, но вы есть друг у друга",
            {"faith": -4, "stability": 8},
            "Кто-то разочарованно вздохнул, кто-то обнял соседа. Крепче стали связи, не алтарь.",
        ),
        Choice(
            "Объявить обычный закат священным знамением",
            {"faith": 5},
            "Закат был красив. Остальное сделала вера.",
        ),
    ],
)

# ── Последствия: разоблачение ────────────────────────────────────────────────

scandal = Event(
    id="scandal",
    weight=2,
    once=True,
    condition=lambda c: "fake_miracle" in c.flags,
    text=lambda c: by_mood(
        c,
        "Человек с зеркалом напился на рынке и рассказал всем, как устроено чудо. "
        "Включая технические подробности и название зеркальщика.",
        "Слух о «чуде» дошёл до паствы: всё было подстроено. "
        "Люди смотрят на алтарь иначе.",
    ),
    choices=[
        Choice(
            "Публично покаяться",
            {"faith": -12, "stability": 6},
            "Каяться было неприятно. Но паства ценит честность, особенно если "
            "её поймали на обмане.",
        ),
        Choice(
            "Объявить, что это было испытание веры",
            {"faith": -3, "stability": -2},
            "Паства решила, что проверка веры — это очень по-вашему. Спорить не стали. Пока.",
        ),
        Choice(
            "Заставить «зеркального» замолчать",
            {"faith": -2, "stability": -8, "followers": -1},
            "Больше он ничего никому не расскажет. Остальные это заметили.",
        ),
    ],
)

# ══════════════════════════════════════════════════════════════════════════════
#  ЛИЧНЫЕ СЮЖЕТЫ: у каждого события есть герой (cult.subject),
#  а его выбор запоминается во flags последователя и аукается позже.
# ══════════════════════════════════════════════════════════════════════════════

# ── Игнат: тайна речного духа (3 события в цепочке) ─────────────────────────


def _ignat(c: Cult):
    return named(c, "Игнат")


def _ignat_secret_subject(c: Cult):
    f = _ignat(c)
    return f if f and c.day >= 4 and not f.flags else None


def _ignat_tolerated(c: Cult, rng: random.Random) -> None:
    shift_loyalty(c.subject, +10)
    c.subject.flags.add("tolerated")


def _ignat_renounced(c: Cult, rng: random.Random) -> None:
    shift_loyalty(c.subject, -25)
    c.subject.flags.add("renounced")


def _ignat_syncretism(c: Cult, rng: random.Random) -> None:
    shift_loyalty(c.subject, +20)
    c.subject.flags.add("syncretism")


ignat_secret = Event(
    id="ignat_secret",
    weight=4,
    once=True,
    subject=_ignat_secret_subject,
    text=lambda c: by_mood(
        c,
        "Фома ночью заметил, что Игнат тайком уходит к реке, и, конечно, пошёл следом. "
        "Вернулся бледный: Игнат разложил на камне крошечный алтарь и бормочет молитву "
        "какому-то речному духу. Фома требует разбирательства. Громко.",
        "Фома выследил Игната: тот молится у реки какому-то другому богу. Фома побелел "
        "от гнева и требует расправы. Паства уже шепчется.",
    ),
    choices=[
        Choice(
            "Закрыть глаза: пусть молится, кому хочет",
            {"stability": -3},
            "Фома остался недоволен, Игнат благодарен. Вы оба сделали вид, "
            "что ничего не было. Пока.",
            action=_ignat_tolerated,
        ),
        Choice(
            "Потребовать публичного отречения",
            {"faith": 5, "stability": -4},
            "Игнат отрёкся: громко, чётко и с таким лицом, которое потом долго помнят.",
            action=_ignat_renounced,
        ),
        Choice(
            "Предложить вписать речного духа в пантеон",
            {"faith": -3, "stability": 2},
            "Богословский совет длился до рассвета. Речной Дух получил статус "
            "«младшего покровителя». Игнат плакал от счастья, Фома от возмущения.",
            action=_ignat_syncretism,
        ),
    ],
)


def _ignat_gift_subject(c: Cult):
    f = _ignat(c)
    if f and ({"tolerated", "syncretism"} & f.flags) and "gift" not in f.flags:
        return f
    return None


def _ignat_gift_text(c: Cult) -> str:
    if "syncretism" in c.subject.flags:
        return ("На рассвете Игнат явился с корзиной свежей рыбы: «Речной Дух благодарит "
                "за признание». Рыба, надо признать, выглядит убедительнее многих чудес.")
    return ("Игнат молча починил прохудившуюся крышу храма и хотел уйти незамеченным. "
            "Потом всё же сказал, что это за ту ночь, когда ты сделал вид, что ничего не видел.")


def _ignat_gift_thanks(c: Cult, rng: random.Random) -> None:
    shift_loyalty(c.subject, +5)
    c.subject.flags.add("gift")


def _ignat_gift_credit(c: Cult, rng: random.Random) -> None:
    shift_loyalty(c.subject, -10)
    c.subject.flags.add("gift")


ignat_gift = Event(
    id="ignat_gift",
    weight=3,
    once=True,
    subject=_ignat_gift_subject,
    text=_ignat_gift_text,
    choices=[
        Choice(
            "Принять дар с искренней благодарностью",
            {"food": 8, "stability": 3},
            "Игнат смутился, кивнул и поспешил заняться делами. Видно было: "
            "он давно не слышал «спасибо» в этих стенах.",
            action=_ignat_gift_thanks,
        ),
        Choice(
            "Принять и объявить это милостью Великого Пробуждённого",
            {"food": 8, "faith": 6},
            "Паства впечатлена. Игнат не сказал ни слова, но по лицу было видно: "
            "он что-то записал себе в уме.",
            action=_ignat_gift_credit,
        ),
    ],
)


def _ignat_grudge_subject(c: Cult):
    f = _ignat(c)
    return f if f and "renounced" in f.flags and "grudge" not in f.flags else None


def _grudge_forgive(c: Cult, rng: random.Random) -> None:
    shift_loyalty(c.subject, +30)
    c.subject.flags.add("grudge")


def _grudge_ignore(c: Cult, rng: random.Random) -> None:
    shift_loyalty(c.subject, -10)
    c.subject.flags.add("grudge")


def _grudge_expel(c: Cult, rng: random.Random) -> None:
    c.followers.remove(c.subject)


ignat_grudge = Event(
    id="ignat_grudge",
    weight=3,
    once=True,
    subject=_ignat_grudge_subject,
    text=lambda c: by_mood(
        c,
        "С тех пор как Игнат публично отрёкся, он ходит мрачный и работает вполсилы. "
        "Сегодня его видели у ворот: стоит с узелком и долго смотрит на дорогу.",
        "Игнат больше не смотрит тебе в глаза. Сегодня он стоял у ворот с узелком. "
        "Паства делает вид, что не замечает.",
    ),
    choices=[
        Choice(
            "Простить публично и вернуть ему место у алтаря",
            {"stability": 3, "faith": -2},
            "Игнат вернулся: смущённый, но на месте. Фома поворчал и смирился.",
            action=_grudge_forgive,
        ),
        Choice(
            "Не вмешиваться",
            {"stability": -2},
            "Игнат постоял у ворот. Постоял ещё. К ужину вернулся, но взгляд у него "
            "теперь другой.",
            action=_grudge_ignore,
        ),
        Choice(
            "Выставить за ворота",
            {"faith": 2, "stability": -5},
            "Игнат ушёл, не оглядываясь. Узелок был лёгким, а ворота тяжёлыми.",
            action=_grudge_expel,
        ),
    ],
)

# ── Марта: болтовня как ресурс ───────────────────────────────────────────────


def _marta_subject(c: Cult):
    f = named(c, "Марта")
    if f and c.day >= 2 and f.loyalty >= 55 and not ({"herald", "gagged"} & f.flags):
        return f
    return None


def _marta_herald(c: Cult, rng: random.Random) -> None:
    c.subject.flags.add("herald")


def _marta_gag(c: Cult, rng: random.Random) -> None:
    shift_loyalty(c.subject, -10)
    c.subject.flags.add("gagged")


def _marta_free(c: Cult, rng: random.Random) -> None:
    c.subject.flags.add("gagged")  # выбор сделан, повторно не предлагаем


marta_gossip = Event(
    id="marta_gossip",
    weight=3,
    once=True,
    subject=_marta_subject,
    text=lambda c: by_mood(
        c,
        "Марта, как обычно, не удержалась и пересказала твою последнюю проповедь "
        "всей округе. Дважды. С добавлениями, в которых ты сам себя не узнал. "
        "Но люди слушают.",
        "Марта разносит слова проповеди по округе: в трёх вариантах и с добавлениями. "
        "Часть слухов приукрашена, часть пугает.",
    ),
    choices=[
        Choice(
            "Назначить её официальным Глашатаем",
            {"faith": 3},
            "Марта получила плащ и титул. Теперь её болтовня священная миссия, "
            "и остановить её невозможно.",
            action=_marta_herald,
        ),
        Choice(
            "Попросить говорить поменьше",
            {"stability": 3},
            "Марта обиженно поджала губы. Слухи поутихли. Зато поутихла и она сама.",
            action=_marta_gag,
        ),
        Choice(
            "Дать ей говорить как есть",
            {"faith": 4, "stability": -3, "followers": 1},
            "Слухи привели одного любопытного. Он же и остался: хотел посмотреть, "
            "правда ли всё это.",
            action=_marta_free,
        ),
    ],
)

# ── Агата: видение ───────────────────────────────────────────────────────────


def _agata_subject(c: Cult):
    f = named(c, "Агата")
    return f if f and c.day >= 5 and not f.flags else None


def _agata_prophecy(c: Cult, rng: random.Random) -> None:
    shift_loyalty(c.subject, +15)
    c.subject.flags.add("prophet")


def _agata_check(c: Cult, rng: random.Random) -> None:
    c.subject.flags.add("checked")
    if rng.random() < 0.5:
        c.flags.add("vision_true")
        apply_effects(c, {"food": 8, "faith": 3}, rng)
    else:
        apply_effects(c, {"faith": -3}, rng)


def _agata_hush(c: Cult, rng: random.Random) -> None:
    shift_loyalty(c.subject, -5)
    c.subject.flags.add("hushed")


agata_vision = Event(
    id="agata_vision",
    weight=3,
    once=True,
    subject=_agata_subject,
    text=lambda c: by_mood(
        c,
        "Агата пришла бледная и взволнованная: ей приснилось, что Великий Пробуждённый "
        "стоял посреди поля, а вокруг росла капуста размером с телегу. "
        "Она уверена, что это знак.",
        "Агата пришла бледная, с дрожащими руками: во сне ей явился Великий Пробуждённый, "
        "и сон был тревожным. Она уверена, что это знак, но не помнит, к добру или к худу.",
    ),
    choices=[
        Choice(
            "Объявить видение пророчеством",
            {"faith": 8, "stability": -3},
            "Агата не знала, куда деть глаза, а паства уже несла ей цветы. "
            "Теперь придётся следить, чтобы ей снилось что-нибудь подходящее.",
            action=_agata_prophecy,
        ),
        Choice(
            "Расспросить подробнее и проверить",
            {},
            lambda c: (
                "В поле, на которое указал сон, нашёлся старый погреб с запасами. "
                "Агата смотрит на тебя так, будто ты сам его туда положил."
                if "vision_true" in c.flags
                else "Расспросы показали, что капуста приснилась после слишком плотного ужина. "
                     "Паства слегка разочарована, Агата сильно."
            ),
            action=_agata_check,
        ),
        Choice(
            "Мягко попросить не рассказывать другим",
            {"stability": 2},
            "Агата кивнула и ушла, прижимая сон к груди, как котёнка.",
            action=_agata_hush,
        ),
    ],
)

EVENTS = [
    sermon, hunger, doubter, newcomers, rival, miracle, scandal,
    ignat_secret, ignat_gift, ignat_grudge, marta_gossip, agata_vision,
]
