import asyncio

from weatherbot.infrastructure.setup import get_user_service, setup_container
from weatherbot.presentation.i18n import i18n


async def async_demo_localization():
    print("=== Localization Demo ===")

    setup_container()
    user_service = get_user_service()

    languages = i18n.get_available_languages()
    print(f"Available languages: {languages}")

    print("\n=== Base translations ===")
    for lang in ["ru", "en", "de"]:
        print(f"\nLanguage: {lang}")
        print(f"start_message: {i18n.get('start_message', lang)[:80]}...")
        print(f"weather_city_button: {i18n.get('weather_city_button', lang)}")
        print(f"weather_home_button: {i18n.get('weather_home_button', lang)}")
        print(f"set_home_button: {i18n.get('set_home_button', lang)}")

    print("\n=== User language operations ===")
    test_chat_id = 12345
    await user_service.create_user(test_chat_id, "test_user")
    user = await user_service.get_user(test_chat_id)
    print(f"Default language: {user.language}")

    for target in ["en", "de", "ru"]:
        await user_service.set_user_language(test_chat_id, target)
        user = await user_service.get_user(test_chat_id)
        print(f"Switched to: {user.language}")

    print("\n=== Parameterized message ===")
    for lang, city in [("ru", "Moscow"), ("en", "Moscow"), ("de", "Moskau")]:
        msg = i18n.get("sethome_success", lang, location=city, lat=55.75, lon=37.61)
        print(f"{lang}: {msg}")

    await user_service.delete_user(test_chat_id)
    print("\n✅ Demo complete")


def main():
    asyncio.run(async_demo_localization())


if __name__ == "__main__":
    main()
