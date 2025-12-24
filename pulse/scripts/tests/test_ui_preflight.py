#!/usr/bin/env python3
"""
Integration tests for ui_preflight.py
Run with: python3 -m unittest scripts.tests.test_ui_preflight -v

Test categories:
- Comment stripping (line, block, nested, raw strings, multiline)
- Mode view filename classification
- Settings access detection (spoofs vs valid escapes)
- Regex correctness
"""

import tempfile
import unittest
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))
from ui_preflight import (
    UIPreflightChecker, 
    strip_comments_preserving_strings,
    SFSYMBOL_SETTINGS_RE,
    SETTINGS_WORDS_RE,
    MORE_MENU_RE,
)


class TestStripComments(unittest.TestCase):
    """Unit tests for comment stripping."""
    
    # === Line comments ===
    
    def test_no_truncation_after_first_comment(self):
        sample = 'let a = 1 // comment\nlet b = "gear"\nlet c = 2'
        out = strip_comments_preserving_strings(sample)
        self.assertIn('let b', out)
        self.assertIn('let c', out)
        self.assertIn('gear', out)
    
    def test_multiple_line_comments(self):
        sample = '// header\nlet a = 1 // inline\nlet b = 2 // another'
        out = strip_comments_preserving_strings(sample)
        self.assertIn('let a', out)
        self.assertIn('let b', out)
        self.assertNotIn('header', out)
        self.assertNotIn('inline', out)
    
    # === Block comments ===
    
    def test_block_comments_stripped(self):
        sample = 'let x = 1 /* block comment */ let y = "gear"'
        out = strip_comments_preserving_strings(sample)
        self.assertNotIn('block comment', out)
        self.assertIn('gear', out)
    
    def test_nested_block_comments(self):
        sample = 'let a = 1 /* outer /* inner */ still outer */ let b = "gear"'
        out = strip_comments_preserving_strings(sample)
        self.assertNotIn('outer', out)
        self.assertNotIn('inner', out)
        self.assertIn('let b', out)
    
    def test_block_comment_spoof_prevented(self):
        sample = 'let x = 1 /* gear */ .toolbar'
        out = strip_comments_preserving_strings(sample)
        self.assertNotIn('gear', out)
        self.assertIn('toolbar', out)
    
    def test_unterminated_block_comment_is_conservative(self):
        """Unterminated /* should strip rest of file (conservative)."""
        sample = 'let a = 1 /* unterminated\nlet b = "gear"'
        out = strip_comments_preserving_strings(sample)
        self.assertIn('let a', out)
        # Rest is inside unterminated block comment - stripped
        self.assertNotIn('gear', out)
    
    # === Strings ===
    
    def test_url_in_string_preserved(self):
        sample = 'Text("http://example.com") // comment'
        out = strip_comments_preserving_strings(sample)
        self.assertIn('http://example.com', out)
        self.assertNotIn('comment', out)
    
    def test_multiline_string_preserved(self):
        sample = '''let s = """
http://example.com
some text // not a comment
"""
.toolbar // real comment'''
        out = strip_comments_preserving_strings(sample)
        self.assertIn('// not a comment', out)  # Inside string
        self.assertNotIn('real comment', out)   # Outside string
    
    def test_escaped_quote_in_string(self):
        sample = r'let s = "say \"hello\"" // comment'
        out = strip_comments_preserving_strings(sample)
        self.assertIn('hello', out)
        self.assertNotIn('comment', out)
    
    # === Raw strings with embedded quotes ===
    
    def test_raw_string_with_embedded_quote(self):
        """Raw string #"he said "hi""# should preserve content."""
        sample = r'let s = #"he said "hi""# // comment'
        out = strip_comments_preserving_strings(sample)
        self.assertIn('he said', out)
        self.assertIn('hi', out)
        self.assertNotIn('comment', out)
    
    def test_raw_multiline_string(self):
        """Raw multiline #\"\"\"...\"\"\"# should preserve content."""
        sample = '''let s = #"""
line with // not a comment
and "quotes" inside
"""#
.toolbar // real comment'''
        out = strip_comments_preserving_strings(sample)
        self.assertIn('// not a comment', out)
        self.assertIn('quotes', out)
        self.assertNotIn('real comment', out)


class TestRegexCorrectness(unittest.TestCase):
    """Unit tests for compiled regexes."""
    
    # === SFSYMBOL_SETTINGS_RE ===
    
    def test_sfsymbol_normal_string(self):
        self.assertIsNotNone(SFSYMBOL_SETTINGS_RE.search('Image(systemName: "gear")'))
        self.assertIsNotNone(SFSYMBOL_SETTINGS_RE.search('Image(systemName: "gearshape")'))
        self.assertIsNotNone(SFSYMBOL_SETTINGS_RE.search('Image(systemName: "gearshape.fill")'))
        self.assertIsNotNone(SFSYMBOL_SETTINGS_RE.search('Image(systemName: "ellipsis")'))
        self.assertIsNotNone(SFSYMBOL_SETTINGS_RE.search('Image(systemName: "ellipsis.circle")'))
    
    def test_sfsymbol_raw_string(self):
        self.assertIsNotNone(SFSYMBOL_SETTINGS_RE.search('Image(systemName: #"gear"#)'))
        self.assertIsNotNone(SFSYMBOL_SETTINGS_RE.search('Image(systemName: ##"gear"##)'))
    
    def test_sfsymbol_systemimage(self):
        """Label(systemImage:) is common in SwiftUI."""
        self.assertIsNotNone(SFSYMBOL_SETTINGS_RE.search('Label("Settings", systemImage: "gear")'))
        self.assertIsNotNone(SFSYMBOL_SETTINGS_RE.search('Label("Menu", systemImage: #"ellipsis"#)'))
    
    def test_sfsymbol_rejects_plain_text(self):
        self.assertIsNone(SFSYMBOL_SETTINGS_RE.search('Text("gear")'))
        self.assertIsNone(SFSYMBOL_SETTINGS_RE.search('let gear = "value"'))
    
    def test_sfsymbol_case_insensitive(self):
        self.assertIsNotNone(SFSYMBOL_SETTINGS_RE.search('Image(SystemName: "Gear")'))
    
    # === SETTINGS_WORDS_RE ===
    
    def test_settings_words_toolbar_proximity(self):
        self.assertIsNotNone(SETTINGS_WORDS_RE.search('.toolbar { SettingsView() }'))
        self.assertIsNotNone(SETTINGS_WORDS_RE.search('NavigationLink(destination: SettingsView())'))
    
    def test_settings_words_rejects_distant(self):
        # 200+ chars apart should not match (window is 120)
        distant = 'toolbar { ' + 'x' * 150 + ' } settings'
        self.assertIsNone(SETTINGS_WORDS_RE.search(distant))
    
    # === MORE_MENU_RE ===
    
    def test_more_menu_body_context(self):
        self.assertIsNotNone(MORE_MENU_RE.search('Menu { Button("More") }'))
        self.assertIsNotNone(MORE_MENU_RE.search('Image(systemName: "ellipsis")'))
        self.assertIsNotNone(MORE_MENU_RE.search('Label("X", systemImage: "ellipsis")'))
    
    def test_more_menu_label_form(self):
        """Menu("More") { ... } is the common label form."""
        self.assertIsNotNone(MORE_MENU_RE.search('Menu("More") { Button("X") {} }'))
        self.assertIsNotNone(MORE_MENU_RE.search('Menu(#"More"#) { }'))
    
    def test_more_menu_rejects_plain_text(self):
        self.assertIsNone(MORE_MENU_RE.search('Text("Learn More")'))
        self.assertIsNone(MORE_MENU_RE.search('Button("More Info")'))  # Not a Menu


class TestModeViewFilename(unittest.TestCase):
    """Tests for mode view filename classification."""
    
    def run_checker(self, files: dict) -> UIPreflightChecker:
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp)
            for name, contents in files.items():
                (p / name).write_text(contents)
            c = UIPreflightChecker(p)
            c.run_all_checks()
            return c
    
    def get_trapped_issues(self, checker, filename=None):
        issues = [i for i in checker.issues if 'TRAPPED' in i['message']]
        if filename:
            issues = [i for i in issues if filename in i['file']]
        return issues
    
    MINIMAL_VIEW = 'import SwiftUI\nstruct {name}: View {{ var body: some View {{ Text("Hi") }} }}'
    
    # === Should match (mode views) ===
    
    def test_sherpa_mode_view_matches(self):
        c = self.run_checker({"SherpaModeView.swift": self.MINIMAL_VIEW.format(name="SherpaModeView")})
        self.assertTrue(len(self.get_trapped_issues(c)) > 0)
    
    def test_rescue_mode_view_matches(self):
        c = self.run_checker({"RescueModeView.swift": self.MINIMAL_VIEW.format(name="RescueModeView")})
        self.assertTrue(len(self.get_trapped_issues(c)) > 0)
    
    def test_pro_mode_matches(self):
        c = self.run_checker({"ProMode.swift": self.MINIMAL_VIEW.format(name="ProMode")})
        self.assertTrue(len(self.get_trapped_issues(c)) > 0)
    
    def test_pro_mode_screen_matches(self):
        c = self.run_checker({"ProModeScreen.swift": self.MINIMAL_VIEW.format(name="ProModeScreen")})
        self.assertTrue(len(self.get_trapped_issues(c)) > 0)
    
    def test_expert_mode_view_matches(self):
        c = self.run_checker({"ExpertModeView.swift": self.MINIMAL_VIEW.format(name="ExpertModeView")})
        self.assertTrue(len(self.get_trapped_issues(c)) > 0)
    
    def test_advanced_mode_view_matches(self):
        c = self.run_checker({"AdvancedModeView.swift": self.MINIMAL_VIEW.format(name="AdvancedModeView")})
        self.assertTrue(len(self.get_trapped_issues(c)) > 0)
    
    # === Should NOT match (not mode views) ===
    
    def test_promo_view_does_not_match(self):
        c = self.run_checker({"PromoView.swift": self.MINIMAL_VIEW.format(name="PromoView")})
        self.assertEqual(len(self.get_trapped_issues(c)), 0)
    
    def test_pro_view_does_not_match(self):
        """ProView (without 'mode') should NOT match."""
        c = self.run_checker({"ProView.swift": self.MINIMAL_VIEW.format(name="ProView")})
        self.assertEqual(len(self.get_trapped_issues(c)), 0)
    
    def test_viewmodel_does_not_match(self):
        """ViewModel suffix should NOT match."""
        c = self.run_checker({"ProModeViewModel.swift": 'class ProModeViewModel {}'})
        self.assertEqual(len(self.get_trapped_issues(c)), 0)


class TestSettingsAccessSpoofs(unittest.TestCase):
    """Tests for spoof attempts that should NOT suppress USER TRAPPED."""
    
    def run_checker(self, files: dict) -> UIPreflightChecker:
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp)
            for name, contents in files.items():
                (p / name).write_text(contents)
            c = UIPreflightChecker(p)
            c.run_all_checks()
            return c
    
    def get_trapped_issues(self, checker, filename=None):
        issues = [i for i in checker.issues if 'TRAPPED' in i['message']]
        if filename:
            issues = [i for i in issues if filename in i['file']]
        return issues
    
    def test_text_settings_does_not_suppress(self):
        c = self.run_checker({
            "ProModeView.swift": '''
import SwiftUI
struct ProModeView: View {
    var body: some View { Text("Settings") }
}
'''
        })
        self.assertTrue(len(self.get_trapped_issues(c)) > 0,
            "Text('Settings') should NOT suppress")
    
    def test_text_gear_does_not_suppress(self):
        c = self.run_checker({
            "SherpaModeView.swift": '''
import SwiftUI
struct SherpaModeView: View {
    var body: some View { Text("gear") }
}
'''
        })
        self.assertTrue(len(self.get_trapped_issues(c)) > 0,
            "Text('gear') should NOT suppress")
    
    def test_comment_gear_does_not_suppress(self):
        c = self.run_checker({
            "RescueModeView.swift": '''
import SwiftUI
struct RescueModeView: View {
    // gear icon here
    var body: some View { Text("Hi") }
}
'''
        })
        self.assertTrue(len(self.get_trapped_issues(c)) > 0,
            "Comment 'gear' should NOT suppress")
    
    def test_block_comment_gear_does_not_suppress(self):
        c = self.run_checker({
            "ExpertModeView.swift": '''
import SwiftUI
struct ExpertModeView: View {
    /* gear settings */
    var body: some View { Text("Hi") }
}
'''
        })
        self.assertTrue(len(self.get_trapped_issues(c)) > 0,
            "Block comment 'gear' should NOT suppress")
    
    def test_text_more_does_not_suppress(self):
        c = self.run_checker({
            "AdvancedModeView.swift": '''
import SwiftUI
struct AdvancedModeView: View {
    var body: some View { Text("Learn More") }
}
'''
        })
        self.assertTrue(len(self.get_trapped_issues(c)) > 0,
            "Text('Learn More') should NOT suppress")


class TestSettingsAccessValid(unittest.TestCase):
    """Tests for valid escape routes that SHOULD suppress USER TRAPPED."""
    
    def run_checker(self, files: dict) -> UIPreflightChecker:
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp)
            for name, contents in files.items():
                (p / name).write_text(contents)
            c = UIPreflightChecker(p)
            c.run_all_checks()
            return c
    
    def get_trapped_issues(self, checker, filename=None):
        issues = [i for i in checker.issues if 'TRAPPED' in i['message']]
        if filename:
            issues = [i for i in issues if filename in i['file']]
        return issues
    
    def test_systemname_gear_suppresses(self):
        c = self.run_checker({
            "SherpaModeView.swift": '''
import SwiftUI
struct SherpaModeView: View {
    var body: some View {
        Text("Hi").toolbar { Image(systemName: "gear") }
    }
}
'''
        })
        self.assertEqual(len(self.get_trapped_issues(c)), 0,
            "systemName: 'gear' SHOULD suppress")
    
    def test_raw_string_systemname_suppresses(self):
        c = self.run_checker({
            "RescueModeView.swift": '''
import SwiftUI
struct RescueModeView: View {
    var body: some View {
        Text("Hi").toolbar { Image(systemName: #"gear"#) }
    }
}
'''
        })
        self.assertEqual(len(self.get_trapped_issues(c)), 0,
            "Raw string systemName SHOULD suppress")
    
    def test_navigationlink_to_settings_suppresses(self):
        c = self.run_checker({
            "ProModeView.swift": '''
import SwiftUI
struct ProModeView: View {
    var body: some View {
        NavigationLink(destination: SettingsView()) { Text("Go") }
    }
}
'''
        })
        self.assertEqual(len(self.get_trapped_issues(c)), 0,
            "NavigationLink to SettingsView SHOULD suppress")
    
    def test_toolbar_with_settings_suppresses(self):
        c = self.run_checker({
            "ExpertModeView.swift": '''
import SwiftUI
struct ExpertModeView: View {
    var body: some View {
        Text("Hi").toolbar { NavigationLink("Settings", destination: SettingsView()) }
    }
}
'''
        })
        self.assertEqual(len(self.get_trapped_issues(c)), 0,
            "Toolbar with Settings SHOULD suppress")
    
    def test_ellipsis_menu_suppresses(self):
        c = self.run_checker({
            "AdvancedModeView.swift": '''
import SwiftUI
struct AdvancedModeView: View {
    var body: some View {
        Menu { Button("More") { } }.toolbar { Image(systemName: "ellipsis") }
    }
}
'''
        })
        self.assertEqual(len(self.get_trapped_issues(c)), 0,
            "Ellipsis menu SHOULD suppress")


if __name__ == "__main__":
    unittest.main(verbosity=2)
