import asyncio

from weatherbot.infrastructure.setup import get_user_service, setup_container
from weatherbot.presentation.i18n import i18n


async def async_test_localization():
    print("=== Testing localization system ===")

    setup_container()
    user_service = get_user_service()

    languages = i18n.get_available_languages()
    print(f"Available languages: {languages}")

    print("\n=== Translation test ===")
    for lang in ["ru", "en", "de"]:
        print(f"\nLanguage: {lang}")
        print(f"start_message: {i18n.get('start_message', lang)[:100]}...")
        print(f"weather_city_button: {i18n.get('weather_city_button', lang)}")
        print(f"weather_home_button: {i18n.get('weather_home_button', lang)}")
        print(f"set_home_button: {i18n.get('set_home_button', lang)}")

    print("\n=== User service test ===")
    test_chat_id = 12345

    try:
        await user_service.create_user(test_chat_id, "test_user")
        user = await user_service.get_user(test_chat_id)
        print(f"Default language for new user: {user.language}")

        await user_service.set_user_language(test_chat_id, "en")
        user = await user_service.get_user(test_chat_id)
        print(f"Language after setting 'en': {user.language}")

        await user_service.set_user_language(test_chat_id, "de")
        user = await user_service.get_user(test_chat_id)
        print(f"Language after setting 'de': {user.language}")
    except Exception as e:
        print(f"Error working with user: {e}")

    print("\n=== Parameterized translation test ===")
    for lang, city in [("ru", "Москва"), ("en", "Moscow"), ("de", "Moskau")]:
        success_msg = i18n.get(
            "sethome_success", lang, location=city, lat=55.7558, lon=37.6173
        )
        lang_name = {"ru": "Russian", "en": "English", "de": "German"}[lang]
        print(f"{lang_name}: {success_msg}")

    german_buttons = {
        "city": i18n.get("weather_city_button", "de"),
        "home": i18n.get("weather_home_button", "de"),
        "set": i18n.get("set_home_button", "de"),
        "remove": i18n.get("remove_home_button", "de"),
    }
    print(f"German buttons: {german_buttons}")

    try:
        await user_service.delete_user(test_chat_id)
        print("Test data cleaned up")
    except Exception as e:
        print(f"Error during cleanup: {e}")
    print("\n✅ Testing completed!")


def test_localization():
    asyncio.run(async_test_localization())


def main():
    asyncio.run(async_test_localization())


if __name__ == "__main__":
    main()
