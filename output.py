import os
import os.path
import sys

class OutputFormat (object):
    "Handles book output. Big FIXME required to make sense."
    def __init__(self, templates, quote):
        self.templates = templates
        self.quote = quote

    def format_begin(self, bookconfig):
        # FIXME make sure book config is properly quoted
        return self.format_with_template("begin", bookconfig)

    def format_intro_sections(self, introsections, shuffled_sections):
        res = ""
        for s in introsections:
            if not s.hastag('dummy'):
                res += self.format_intro_section(s, shuffled_sections)
        return res

    def format_intro_section(self, section, shuffled_sections):
        # FIXME some serious code-duplication here
        refs = []
        refsdict = ReferenceFormatter(section.nr,
                                      shuffled_sections.name_to_nr,
                                      self.format_with_template("section_ref"),
                                      self.quote)
        formatted_text = self.format_section(section, refsdict)
        return self.format_with_template("introsection", {
            'name' : section.name,
            'text' : formatted_text,
            'refs' : '\n'.join(refsdict.getfound()) # hack for DOT output
        })

    def format_sections_begin(self, bookconfig):
        return self.format_with_template("sections_begin",
                                         bookconfig)

    def format_shuffled_sections(self, shuffled_sections):
        res = ""
        for i, p in enumerate(shuffled_sections.as_list):
            if p and not p.hastag('dummy'):
                res += self.format_section(p, shuffled_sections)
            elif i > 0:
                res += self.format_empty_section(i)
        return res

    def format_section(self, section, shuffled_sections):
        refs = []
        refsdict = ReferenceFormatter(section.nr,
                                      shuffled_sections.name_to_nr,
                                      self.format_with_template("section_ref"),
                                      self.quote)
        formatted_text = self.format_section_body(section, refsdict)
        return self.format_with_template("section", {
            'nr' : section.nr,
            'name' : section.name,
            'text' : formatted_text,
            'refs' : '\n'.join(refsdict.getfound()) # hack for DOT output
        })

    def format_section_body(self, section, references):
        i = 0
        res = ""
        # FIXME refactor for readability once good tests are in place
        while i < len(section.text):
            ref_start = section.text.find('[[', i)
            tag_start = section.text.find('[', i)
            if ref_start >= 0 and ref_start <= tag_start:
                res += self.quote(section.text[i:ref_start])
                ref_end = section.text.find(']]', ref_start)
                if ref_end > ref_start:
                    ref = section.text[ref_start+2:ref_end]
                    splitref = ref.split()
                    if len(splitref) > 1:
                        for refmod in splitref[:-1]:
                            res += self.format_with_template(refmod,
                                                             references)
                    res += references[splitref[-1]]
                    i = ref_end + 2
                else:
                    raise Exception('Mismatched ref start [[ in section %s' %
                                    self.name)
            elif tag_start >= 0:
                res += self.quote(section.text[i:tag_start])
                tag_end = section.text.find(']', tag_start)
                if tag_end < 0:
                    raise Exception('Mismatched tag start [ in section %s' %
                                    self.name)
                tag = section.text[tag_start+1:tag_end].strip()
                tagparts = tag.split()
                tagname = tagparts[0]
                end_tag_start = section.text.find('[', tag_end)
                if (not end_tag_start > tag_end
                    and section.text[end_tag_start].startswith('[/' + tagname
                                                               + ']')):
                    raise Exception('Bad format %s tag in %s.' % (
                        tag, self.name))
                inner = section.text[tag_end+1:end_tag_start]
                # FIXME this pollutes the mutable references object
                references['inner'] = self.quote(self.quote(inner))
                for i, arg in enumerate(tagparts[1:]):
                    references['arg%d' % (i+1)] = self.quote(arg)
                f = self.format_with_template(tagname,
                                              references)
                if len(f) > 0:
                    res += f
                else:
                    res += self.quote(inner)
                i = section.text.find(']', end_tag_start) + 1
            else:
                res += self.quote(section.text[i:])
                break
        return res

    def format_empty_section(self, nr):
        return self.format_with_template("empty_section", {
            'nr' : nr,
        })

    def format_end(self, bookconfig):
        return self.format_with_template("end", bookconfig)

    def format_with_template(self, name, values=None):
        template = self.templates.get(name)
        if values:
            return template % values
        else:
            return template

class ReferenceFormatter (object):
    "There is probably a better way, but this hack seems to work."
    def __init__(self, from_nr, name_to_nr, ref_template, quote):
        self.from_nr = from_nr
        self.name_to_nr = name_to_nr
        self.found = set()
        self.ref_template = ref_template
        self.items = {'nr' : from_nr}
        self.quote = quote

    def __getitem__(self, key):
        if key in self.items:
            return self.quote(self.items[key])
        to_nr = self.name_to_nr[key]
        res = self.ref_template % {
            'nr' : to_nr,
            'from_nr' : self.from_nr
        }
        if key in self.name_to_nr:
            self.found.add(res)
        return res

    def getfound(self):
        return list(self.found)

    def __setitem__(self, key, value):
        self.items[key] = value

    def __delitem__(self, key):
        del self.items[key]
