use serde::Serialize;
use std::{collections::HashMap, fmt};
use tree_sitter::{Node, Parser};
use tree_sitter_html::LANGUAGE;

#[derive(Debug, Clone, Serialize)]
pub struct TextSegment {
    pub text: String,
    pub tag_path: Vec<HtmlTag>, // Path of HTML tags leading to this text
    pub mwid: String,
    pub section: String,
}

impl TextSegment {
    pub fn text(&self) -> &String {
        &self.text
    }
    /// Check if text node is within a specific tag
    pub fn is_in_tag(&self, tag_name: &str) -> bool {
        self.tag_path.iter().any(|tag| tag.name == tag_name)
    }

    /// Check if text node is within a tag with specific attribute
    pub fn is_in_tag_with_attribute(&self, attr_name: &str, attr_value: Option<&str>) -> bool {
        self.tag_path.iter().any(|tag| {
            if let Some(value) = attr_value {
                tag.get_attribute(attr_name)
                    .map_or_else(|| false, |v| v == value)
            } else {
                tag.has_attribute(attr_name)
            }
        })
    }

    /// Check if text node is within a tag with specific class
    pub fn is_in_tag_with_class(&self, class_name: &str) -> bool {
        self.tag_path.iter().any(|tag| tag.has_class(class_name))
    }

    /// Check if text node is within a tag with specific ID
    pub fn is_in_tag_with_id(&self, id: &str) -> bool {
        self.tag_path.iter().any(|tag| tag.has_id(id))
    }

    /// Get the immediate parent tag
    pub fn get_parent_tag(&self) -> Option<&HtmlTag> {
        self.tag_path.last()
    }

    /// Check if text matches a CSS-like selector path
    pub fn matches_selector_path(&self, selectors: &[&str]) -> bool {
        if selectors.is_empty() || self.tag_path.len() < selectors.len() {
            return false;
        }

        // Check if the last N tags match the selectors
        let start_idx = self.tag_path.len() - selectors.len();
        for (i, selector) in selectors.iter().enumerate() {
            if !self.tag_path[start_idx + i].matches_selector(selector) {
                return false;
            }
        }
        true
    }
}

impl fmt::Display for TextSegment {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        write!(
            f,
            "mwid: {}\nsection: {}\ntext:\n{}\n---",
            self.mwid, self.section, self.text
        )
    }
}
#[derive(Debug, Clone, Serialize)]
pub struct HtmlTag {
    pub name: String,
    pub attributes: HashMap<String, String>,
    pub start_byte: usize,
    pub end_byte: usize,
}

impl HtmlTag {
    pub fn new(name: String, start_byte: usize, end_byte: usize) -> Self {
        Self {
            name,
            attributes: HashMap::new(),
            start_byte,
            end_byte,
        }
    }

    pub fn has_attribute(&self, name: &str) -> bool {
        self.attributes.contains_key(name)
    }

    pub fn get_attribute(&self, name: &str) -> Option<&String> {
        self.attributes.get(name)
    }

    pub fn has_class(&self, class_name: &str) -> bool {
        if let Some(class_attr) = self.get_attribute("class") {
            class_attr.split_whitespace().any(|c| c == class_name)
        } else {
            false
        }
    }

    pub fn get_id(&self) -> String {
        if let Some(id) = self.get_attribute("id") {
            return id.to_string();
        }
        String::new()
    }

    pub fn has_id(&self, id: &str) -> bool {
        self.get_attribute("id").map_or(false, |v| v == id)
    }

    pub fn matches_selector(&self, selector: &str) -> bool {
        // Simple selector matching: tag, .class, #id
        if selector.starts_with('.') {
            self.has_class(&selector[1..])
        } else if selector.starts_with('#') {
            self.has_id(&selector[1..])
        } else {
            self.name == selector
        }
    }
}

#[derive(Debug, Clone)]
struct SectionInfo {
    title: String,
    level: u8, // 1-6 for h1-h6
}

pub struct WikiPage {
    parser: Parser,
    text_segments: Vec<TextSegment>,
    current_sections: Vec<SectionInfo>, // Stack of current section hierarchy
}

impl WikiPage {
    pub fn new() -> Result<Self, Box<dyn std::error::Error>> {
        let language = LANGUAGE.into();
        let mut parser = Parser::new();
        parser.set_language(&language)?;

        Ok(WikiPage {
            parser,
            text_segments: Vec::new(),
            current_sections: Vec::new(),
        })
    }

    pub fn extract_text(&mut self, wikitext: String) -> Result<Vec<TextSegment>, &'static str> {
        self.text_segments.clear();
        self.current_sections.clear();
        let tree = self
            .parser
            .parse(wikitext.as_str(), None)
            .ok_or("Failed to parse HTML")?;
        let source = wikitext.as_bytes();
        self.walk_and_collect(&tree.root_node(), Vec::new(), source);
        Ok(self.text_segments.clone())
    }

    /// Extract plain text from an HTML string, joining paragraphs with double newlines.
    pub fn extract_text_plain(html: &str) -> Result<String, Box<dyn std::error::Error>> {
        let mut page = WikiPage::new()?;
        let segments = page.extract_text(html.to_string()).map_err(|e| e.to_string())?;
        let text = segments
            .iter()
            .map(|s| s.text.trim())
            .filter(|t| !t.is_empty())
            .collect::<Vec<_>>()
            .join("\n\n");
        Ok(text)
    }

    fn get_header_level(tag_name: &str) -> Option<u8> {
        match tag_name {
            "h1" => Some(1),
            "h2" => Some(2),
            "h3" => Some(3),
            "h4" => Some(4),
            "h5" => Some(5),
            "h6" => Some(6),
            _ => None,
        }
    }

    fn extract_text_from_element(&self, node: &Node, source: &[u8]) -> String {
        let mut text = String::new();

        for child in node.children(&mut node.walk()) {
            match child.kind() {
                "text" => {
                    if let Ok(t) = child.utf8_text(source) {
                        text.push_str(t.trim());
                    }
                }
                "element" => {
                    // Recursively extract text from child elements
                    let child_text = self.extract_text_from_element(&child, source);
                    if !child_text.is_empty() {
                        if !text.is_empty() {
                            text.push(' ');
                        }
                        text.push_str(&child_text);
                    }
                }
                _ => {}
            }
        }

        text
    }

    fn update_sections(&mut self, level: u8, title: String) {
        // Remove sections at the same level or deeper
        self.current_sections
            .retain(|section| section.level < level);

        // Add the new section
        self.current_sections.push(SectionInfo { title, level });
    }

    fn get_current_section_string(&self) -> String {
        self.current_sections
            .iter()
            .map(|section| section.title.as_str())
            .collect::<Vec<_>>()
            .join(" - ")
    }

    fn walk_and_collect(&mut self, node: &Node, mut current_tag_path: Vec<HtmlTag>, source: &[u8]) {
        match node.kind() {
            "text" => {
                if let Ok(text) = node.utf8_text(source) {
                    let trimmed_text = text.trim();
                    if !trimmed_text.is_empty() {
                        // Check if we need to create a new text segment
                        let needs_new_segment = self.text_segments.is_empty();

                        if needs_new_segment {
                            self.text_segments.push(TextSegment {
                                text: String::new(),
                                tag_path: current_tag_path.clone(),
                                mwid: String::new(),
                                section: self.get_current_section_string(),
                            });
                        }

                        // Add text to the last text segment
                        let last_index = self.text_segments.len() - 1;
                        if !self.text_segments[last_index].text.is_empty() {
                            self.text_segments[last_index].text.push(' ');
                        }
                        self.text_segments[last_index].text.push_str(trimmed_text);
                    }
                }
            }
            "script_element" | "style_element" => (),
            "element" => {
                // Parse the element and its attributes
                if let Some(html_tag) = self.parse_element(node, source) {
                    if html_tag.name == "link" {
                        return;
                    }

                    let excluded_classes = vec![
                        "shortdescription",
                        "hatnote",
                        "infobox",
                        "reference",
                        "navbox",
                        "noprint",
                        "reflist",
                        "citation",
                    ];

                    for class_name in &excluded_classes {
                        if html_tag.has_class(class_name) {
                            return;
                        }
                    }

                    // Check if this is a header element
                    if let Some(level) = Self::get_header_level(&html_tag.name) {
                        // Extract the text content of the header
                        let header_text = self.extract_text_from_element(node, source);
                        if !header_text.is_empty() {
                            self.update_sections(level, header_text);
                        }

                        // Add the header to the tag path and continue processing
                        current_tag_path.push(html_tag);
                    }
                    // Check if this is a paragraph element
                    else if html_tag.name == "p" {
                        // Create a new text segment for this paragraph
                        let mwid = html_tag.get_id();
                        let mut new_tag_path = current_tag_path.clone();
                        new_tag_path.push(html_tag.clone());

                        self.text_segments.push(TextSegment {
                            text: String::new(),
                            tag_path: new_tag_path.clone(),
                            mwid,
                            section: self.get_current_section_string(),
                        });

                        current_tag_path = new_tag_path;
                    } else {
                        // For non-paragraph elements, just add to the tag path
                        current_tag_path.push(html_tag);
                    }

                    // Process children with updated path
                    for i in 0..node.child_count() {
                        if let Some(child) = node.child(i as u32) {
                            self.walk_and_collect(&child, current_tag_path.clone(), source);
                        }
                    }
                }
            }
            _ => {
                // For other nodes, continue traversing children
                for i in 0..node.child_count() {
                    if let Some(child) = node.child(i as u32) {
                        self.walk_and_collect(&child, current_tag_path.clone(), source);
                    }
                }
            }
        }
    }

    fn parse_element(&self, element_node: &Node, source: &[u8]) -> Option<HtmlTag> {
        // Find the start_tag child
        let start_tag = element_node
            .children(&mut element_node.walk())
            .find(|child| child.kind() == "start_tag")?;

        // Extract tag name
        let tag_name = start_tag
            .children(&mut start_tag.walk())
            .find(|child| child.kind() == "tag_name")?;

        let tag_name_str = tag_name.utf8_text(source).ok()?.to_string();

        let mut html_tag = HtmlTag::new(
            tag_name_str,
            element_node.start_byte(),
            element_node.end_byte(),
        );

        // Parse attributes
        for child in start_tag.children(&mut start_tag.walk()) {
            if child.kind() == "attribute" {
                if let Some((attr_name, attr_value)) = self.parse_attribute(&child, source) {
                    html_tag.attributes.insert(attr_name, attr_value);
                }
            }
        }

        Some(html_tag)
    }

    fn parse_attribute(&self, attr_node: &Node, source: &[u8]) -> Option<(String, String)> {
        let mut attr_name = None;
        let mut attr_value = String::new();

        for child in attr_node.children(&mut attr_node.walk()) {
            match child.kind() {
                "attribute_name" => {
                    attr_name = child.utf8_text(source).ok().map(|s| s.to_string());
                }
                "quoted_attribute_value" => {
                    // Look for attribute_value inside quoted_attribute_value
                    for grandchild in child.children(&mut child.walk()) {
                        if grandchild.kind() == "attribute_value" {
                            if let Ok(value) = grandchild.utf8_text(source) {
                                attr_value = value.to_string();
                            }
                        }
                    }
                }
                "attribute_value" => {
                    // Direct attribute value (unquoted)
                    if let Ok(value) = child.utf8_text(source) {
                        attr_value = value.to_string();
                    }
                }
                _ => {}
            }
        }

        attr_name.map(|name| (name, attr_value))
    }
}

pub async fn get_text(
    language: &str,
    title: &str,
) -> Result<Vec<TextSegment>, Box<dyn std::error::Error>> {
    let wikitext = get_page_content_html(language, title).await.unwrap();
    let mut parser = WikiPage::new().unwrap();
    Ok(parser.extract_text(wikitext).unwrap())
}

async fn get_page_content_html(
    language: &str,
    title: &str,
) -> Result<String, Box<dyn std::error::Error>> {
    let url = format!("https://{language}.wikipedia.org/api/rest_v1/page/html/{title}?stash=false");

    let client = reqwest::Client::new();
    let response = client
        .get(&url)
        .header(
            "User-Agent",
            "Wikitext-Extractor/1.0 (https://github.com/santhostr/wikilink-suggester)",
        )
        .send()
        .await?;
    if !response.status().is_success() {
        return Err(format!("Failed to fetch article: HTTP {}", response.status()).into());
    }

    let html_text = response.text().await?;

    Ok(html_text)
}
