from collections import defaultdict
import json
import zipfile
from lxml import etree

# Define common fonts to ignore
common_fonts = {
    'Times New Roman',
    'Arial',
    'Calibri',
    # Add any other common fonts here
}

# Define elements to ignore
ignored_elements = {
    'proofErr',
    'bookmarkStart',
    'bookmarkEnd',
    'lastRenderedPageBreak',
    'webHidden',
    'numPr',
    'pBdr',
    'ind',
    'spacing',
    'jc',
    'tabs',
    'sectPr',
    'pgMar'
    # Add any other elements to ignore here
}

# Define attributes to ignore
ignored_attributes = {
    'rsidR',
    'rsidRPr',
    'rsidRDefault',
    'rsidP',
    'paraId',
    'textId',
    'rsidR',
    'rsidRPr',
    'rsidDel',
    'rsidP',
    'rsidTr',
    # Add any other attributes to ignore here
}

# Define metadata elements to ignore
ignored_metadata_elements = {
    'application',
    'docSecurity',
    'scaleCrop',
    'linksUpToDate',
    'charactersWithSpaces',
    'hiddenSlides',
    'mmClips',
    'notes',
    'words',
    'characters',
    'pages',
    'lines',
    'paragraphs',
    'company',
    'template',
    # Add any other metadata elements to ignore here
}

def remove_ignored_elements(tree):
    """Remove all ignored elements from the XML tree, except highlights."""
    for elem in tree.xpath(".//*"):
        tag_without_ns = elem.tag.split('}')[-1]
        if tag_without_ns in ignored_elements:
            elem.getparent().remove(elem)
        elif elem.tag == '{http://schemas.openxmlformats.org/wordprocessingml/2006/main}rPr':  # Check for highlights in rPr
            if not any(child.tag.endswith('highlight') for child in elem.getchildren()):
                elem.getparent().remove(elem)
        else:
            # Remove ignored attributes
            for attr in list(elem.attrib):
                attr_without_ns = attr.split('}')[-1]
                if attr_without_ns in ignored_attributes or attr_without_ns.startswith('rsid'):
                    del elem.attrib[attr]
    return tree

def etree_to_dict(t):
    """Convert an lxml etree to a nested dictionary, excluding ignored namespaces and attributes."""
    tag = t.tag.split('}')[-1]  # Remove namespace URI
    if tag in ignored_elements:
        return None

    d = {tag: {} if t.attrib else None}
    children = list(t)
    if children:
        dd = defaultdict(list)
        for dc in filter(None, map(etree_to_dict, children)):
            for k, v in dc.items():
                dd[k].append(v)
        d = {tag: {k: v[0] if len(v) == 1 else v for k, v in dd.items()}}

    if t.attrib:
        # Filter out common fonts and ignored attributes
        filtered_attribs = {}
        for k, v in t.attrib.items():
            k = k.split('}')[-1]  # Remove namespace URI
            if k in ('ascii', 'hAnsi', 'cs', 'eastAsia'):
                if v not in common_fonts:
                    filtered_attribs[k] = v
            elif k not in ignored_attributes and not k.startswith('rsid'):
                filtered_attribs[k] = v
        d[tag].update(filtered_attribs)
    
    if t.text:
        text = t.text.strip()
        # Here we ensure that the text encoding is correctly handled
        text = bytes(text, 'utf-8').decode('utf-8', 'ignore')
        if children or t.attrib:
            if text:
                d[tag]['#text'] = text
        else:
            d[tag] = text
    
    if not t.attrib and not children and not t.text:
        return None

    return d

# Additionally, update the 'remove_ignored_elements' function to fix encoding
def remove_ignored_elements(tree):
    """Remove all ignored elements from the XML tree, except highlights."""
    for elem in tree.xpath(".//*"):
        tag_without_ns = elem.tag.split('}')[-1]
        if tag_without_ns in ignored_elements:
            elem.getparent().remove(elem)
        elif elem.tag == '{http://schemas.openxmlformats.org/wordprocessingml/2006/main}rPr':  # Check for highlights in rPr
            if not any(child.tag.endswith('highlight') for child in elem.getchildren()):
                elem.getparent().remove(elem)
        else:
            # Remove ignored attributes
            for attr in list(elem.attrib):
                attr_without_ns = attr.split('}')[-1]
                if attr_without_ns in ignored_attributes or attr_without_ns.startswith('rsid'):
                    del elem.attrib[attr]
    # Decode the text correctly for each XML element
    for elem in tree.xpath(".//text()"):
        elem_text = elem.strip()
        encoded_text = bytes(elem_text, 'utf-8').decode('utf-8', 'ignore')
        parent = elem.getparent()
        if parent is not None:
            parent.text = encoded_text
    return tree

def extract_metadata(docx):
    """Extract metadata from the document properties, ignoring specified elements."""
    metadata = {}
    with docx.open('docProps/core.xml') as core_xml:
        xml_content = core_xml.read()
        core_tree = etree.XML(xml_content)
        for child in core_tree.getchildren():
            tag = child.tag.split('}')[-1]  # Get tag without namespace
            if tag not in ignored_metadata_elements:
                metadata[tag] = child.text
    return metadata

def process_docx(file_path):
    # Load the document with zipfile and lxml
    with zipfile.ZipFile(file_path) as docx:
        metadata = extract_metadata(docx)
        with docx.open('word/document.xml') as document_xml:
            xml_content = document_xml.read()
            document_tree = etree.XML(xml_content)

            # Remove the ignored elements
            document_tree = remove_ignored_elements(document_tree)

            # Convert the rest of the XML tree to a dictionary
            document_dict = etree_to_dict(document_tree)
            document_dict['metadata'] = metadata  # Add metadata to the document dictionary

            docx_json = json.dumps(document_dict, ensure_ascii=False, indent=2)

            return docx_json
