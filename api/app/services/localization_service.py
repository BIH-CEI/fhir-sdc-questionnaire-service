"""Service for localizing Questionnaires to specific languages."""
from typing import Optional, Dict, Any, List
import logging
import copy

logger = logging.getLogger(__name__)


class LocalizationService:
    """Service for extracting language-specific versions of Questionnaires."""

    def localize(
        self,
        questionnaire: Dict[str, Any],
        language: str
    ) -> Dict[str, Any]:
        """
        Localize a multilingual Questionnaire to a specific language.

        Args:
            questionnaire: Full Questionnaire resource with translations
            language: Target language code (e.g., 'de', 'es', 'fr')

        Returns:
            Questionnaire with only the specified language (no translation extensions)
        """
        # Create a deep copy to avoid modifying original
        localized = copy.deepcopy(questionnaire)

        # Process top-level fields
        localized = self._process_element(localized, language)

        # Process items recursively
        if "item" in localized:
            localized["item"] = self._process_items(localized["item"], language)

        # Set language metadata
        localized["language"] = language

        # Add localization metadata tag
        if "meta" not in localized:
            localized["meta"] = {}
        if "tag" not in localized["meta"]:
            localized["meta"]["tag"] = []

        localized["meta"]["tag"].append({
            "system": "http://example.org/fhir/CodeSystem/localization-tag",
            "code": "localized",
            "display": f"Localized to {language}"
        })

        logger.info(f"Localized Questionnaire to {language}")
        return localized

    def _process_items(
        self,
        items: List[Dict[str, Any]],
        language: str
    ) -> List[Dict[str, Any]]:
        """Process questionnaire items recursively."""
        processed_items = []

        for item in items:
            processed_item = self._process_element(item, language)

            # Process nested items
            if "item" in processed_item:
                processed_item["item"] = self._process_items(
                    processed_item["item"],
                    language
                )

            # Process answer options
            if "answerOption" in processed_item:
                processed_item["answerOption"] = [
                    self._process_element(option, language)
                    for option in processed_item["answerOption"]
                ]

            processed_items.append(processed_item)

        return processed_items

    def _process_element(
        self,
        element: Dict[str, Any],
        language: str
    ) -> Dict[str, Any]:
        """
        Process a single element, extracting localization for specified language.

        Handles fields like: title, text, display, prefix, etc.
        """
        # Fields that can have translations
        translatable_fields = [
            "title", "text", "display", "prefix", "definition",
            "name", "description", "copyright", "publisher"
        ]

        for field in translatable_fields:
            if field in element:
                # Check for translation extension (format: _fieldName)
                extension_field = f"_{field}"
                if extension_field in element:
                    localized_value = self._extract_localization(
                        element[field],
                        element[extension_field],
                        language
                    )

                    if localized_value:
                        # Replace with localized version
                        element[field] = localized_value

                    # Remove extension (no longer needed in localized version)
                    del element[extension_field]

        return element

    def _extract_localization(
        self,
        original_value: str,
        extension_element: Dict[str, Any],
        target_language: str
    ) -> Optional[str]:
        """
        Extract localized text from extension element.

        Supports both:
        - http://hl7.org/fhir/StructureDefinition/translation
        - http://hl7.org/fhir/StructureDefinition/iso21090-ST-translation
        """
        if "extension" not in extension_element:
            return None

        for ext in extension_element.get("extension", []):
            url = ext.get("url", "")

            # Modern translation extension
            if "translation" in url.lower():
                lang = None
                content = None

                # Extract lang and content from sub-extensions
                for sub_ext in ext.get("extension", []):
                    sub_url = sub_ext.get("url", "")
                    if sub_url == "lang":
                        lang = sub_ext.get("valueCode") or sub_ext.get("valueString")
                    elif sub_url == "content":
                        content = sub_ext.get("valueString")

                if lang == target_language and content:
                    return content

            # Legacy ISO 21090 translation
            elif "iso21090" in url.lower():
                lang = ext.get("lang") or ext.get("valueCode")
                content = ext.get("valueString") or ext.get("value")

                if lang == target_language and content:
                    return content

        return None

    def get_available_languages(self, questionnaire: Dict[str, Any]) -> List[str]:
        """
        Get list of available languages in a Questionnaire.

        Args:
            questionnaire: Questionnaire resource

        Returns:
            List of language codes (e.g., ['en', 'de', 'es'])
        """
        languages = set()

        # Check resource-level language (default/base language)
        if "language" in questionnaire:
            languages.add(questionnaire["language"])
        else:
            # Default to 'en' if not specified
            languages.add("en")

        # Scan for translations
        languages.update(self._scan_translations(questionnaire))

        return sorted(list(languages))

    def _scan_translations(self, element: Any) -> set:
        """Recursively scan for all language codes in translation extensions."""
        languages = set()

        if isinstance(element, dict):
            # Check for translation extensions
            for key, value in element.items():
                if key.startswith("_") and isinstance(value, dict):
                    if "extension" in value:
                        for ext in value["extension"]:
                            url = ext.get("url", "")
                            if "translation" in url.lower():
                                # Extract language from sub-extensions
                                for sub_ext in ext.get("extension", []):
                                    if sub_ext.get("url") == "lang":
                                        lang = sub_ext.get("valueCode") or sub_ext.get("valueString")
                                        if lang:
                                            languages.add(lang)

                # Recurse into all values
                languages.update(self._scan_translations(value))

        elif isinstance(element, list):
            for item in element:
                languages.update(self._scan_translations(item))

        return languages

    def validate_language_support(
        self,
        questionnaire: Dict[str, Any],
        language: str
    ) -> bool:
        """
        Check if a Questionnaire has support for a specific language.

        Args:
            questionnaire: Questionnaire resource
            language: Language code to check

        Returns:
            True if language is available, False otherwise
        """
        available = self.get_available_languages(questionnaire)
        return language in available
