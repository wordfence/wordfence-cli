from html import escape
from typing import Dict, Optional, List, Union, Any


class HtmlContent:

    def to_html(self) -> str:
        raise NotImplementedError(
                'HTML content must be able to be converted to a string'
            )

    def __str__(self) -> str:
        return self.to_html()


class RawHtml(HtmlContent):

    def __init__(self, html: str):
        self.html = html

    def to_html(self) -> str:
        return self.html


def to_html(
            content: Optional[List[Union[HtmlContent, str]]] = None
        ) -> str:
    string = ''
    for item in content:
        if isinstance(item, HtmlContent):
            string += item.to_html()
        else:
            string += escape(item)
    return string


class Container(HtmlContent):

    def __init__(
                self,
                content: Optional[List[Union[HtmlContent, str]]] = None
            ):
        self.content = content if content is not None else []

    def append(self, content: Any):
        if not (isinstance(content, HtmlContent) or isinstance(content, str)):
            content = str(content)
        self.content.append(content)
        return self

    def to_html(self) -> str:
        return to_html(self.content)


class Tag(Container):

    def __init__(
                self,
                name: str,
                attributes: Optional[Dict[str, Optional[str]]] = None,
                content: Optional[List[Union[HtmlContent, str]]] = None
            ):
        self.name = name
        self.attributes = attributes if attributes is not None else {}
        super().__init__(content)

    def set_attribute(self, name: str, value: Optional[str] = None):
        self.attributes[name] = value
        return self

    def _format_attributes(self) -> str:
        attribute_string = ''
        for name, value in self.attributes.items():
            name = escape(name)
            value = escape(value)
            attribute_string += f' {name}="{value}"'
        return attribute_string

    def to_html(self) -> str:
        attribute_string = self._format_attributes()
        string = f'<{self.name}{attribute_string}>'
        if len(self.content) > 0:
            string += super().to_html()
            string += f'</{self.name}>'
        return string


class Document(HtmlContent):

    def __init__(self):
        self.head = Tag('head')
        self.body = Tag('body')

    def to_html(self) -> str:
        html = Tag('html')
        html.append(self.head)
        html.append(self.body)
        return html.to_html()


class Style:

    def __init__(
                self,
                selector: str,
                properties: Optional[Dict[str, str]] = None
            ):
        self.selector = selector
        self.properties = properties if properties is not None else {}

    def set(self, property: str, value):
        self.properties[property] = str(value)
        return self

    def __str__(self) -> str:
        css = self.selector + ' {\n'
        for name, value in self.properties.items():
            css += f'\t{name}: {value};\n'
        css += '}'
        return css


class Stylesheet(HtmlContent):

    def __init__(
                self,
                styles: Optional[List[Style]] = None
            ):
        self.styles = styles if styles is not None else []

    def add(self, *styles: Style):
        self.styles.extend(styles)
        return self

    def to_html(self) -> str:
        tag = Tag('style')
        for style in self.styles:
            tag.append(str(style))
        return tag.to_html()
