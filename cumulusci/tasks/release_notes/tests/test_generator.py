# coding=utf-8

import datetime
import httplib
import json
import os
import unittest

import responses

from cumulusci.tasks.release_notes.generator import BaseReleaseNotesGenerator
from cumulusci.tasks.release_notes.generator import StaticReleaseNotesGenerator
from cumulusci.tasks.release_notes.generator import DirectoryReleaseNotesGenerator
from cumulusci.tasks.release_notes.generator import GithubReleaseNotesGenerator
from cumulusci.tasks.release_notes.generator import PublishingGithubReleaseNotesGenerator
from cumulusci.tasks.release_notes.parser import BaseChangeNotesParser
from cumulusci.tasks.release_notes.tests.util_github_api import GithubApiTestMixin

__location__ = os.path.split(os.path.realpath(__file__))[0]


class DummyParser(BaseChangeNotesParser):

    def parse(self, change_note):
        pass

    def _render(self):
        return 'dummy parser output'.format(self.title)


class TestBaseReleaseNotesGenerator(unittest.TestCase):

    def test_render_no_parsers(self):
        release_notes = BaseReleaseNotesGenerator()
        content = release_notes.render()
        self.assertEqual(content, '')

    def test_render_dummy_parsers(self):
        release_notes = BaseReleaseNotesGenerator()
        release_notes.parsers.append(DummyParser('Dummy 1'))
        release_notes.parsers.append(DummyParser('Dummy 2'))
        expected = u'# Dummy 1\r\n\r\ndummy parser output\r\n\r\n' +\
                   u'# Dummy 2\r\n\r\ndummy parser output'
        self.assertEqual(release_notes.render(), expected)


class TestStaticReleaseNotesGenerator(unittest.TestCase):

    def test_init_parser(self):
        release_notes = StaticReleaseNotesGenerator([])
        assert len(release_notes.parsers) == 3


class TestDirectoryReleaseNotesGenerator(unittest.TestCase):

    def test_init_parser(self):
        release_notes = DirectoryReleaseNotesGenerator('change_notes')
        assert len(release_notes.parsers) == 3

    def test_full_content(self):
        change_notes_dir = os.path.join(
            __location__,
            'change_notes',
            'full',
        )
        release_notes = DirectoryReleaseNotesGenerator(
            change_notes_dir,
        )

        content = release_notes()
        expected = "# Critical Changes\r\n\r\n* This will break everything!\r\n\r\n# Changes\r\n\r\nHere's something I did. It was really cool\r\nOh yeah I did something else too!\r\n\r\n# Issues Closed\r\n\r\n#2345\r\n#6236"
        print expected
        print '-------------------------------------'
        print content

        self.assertEqual(content, expected)


class TestGithubReleaseNotesGenerator(unittest.TestCase):

    def setUp(self):
        self.current_tag = 'prod/1.4'
        self.last_tag = 'prod/1.3'
        self.github_info = {
            'github_owner': 'TestOwner',
            'github_repo': 'TestRepo',
            'github_username': 'TestUser',
            'github_password': 'TestPass',
        }

    def test_init_without_last_tag(self):
        github_info = self.github_info.copy()
        generator = GithubReleaseNotesGenerator(github_info, self.current_tag)
        self.assertEqual(generator.github_info, github_info)
        self.assertEqual(generator.current_tag, self.current_tag)
        self.assertEqual(generator.last_tag, None)
        self.assertEqual(generator.change_notes.current_tag, self.current_tag)
        self.assertEqual(generator.change_notes._last_tag, None)

    def test_init_with_last_tag(self):
        github_info = self.github_info.copy()
        generator = GithubReleaseNotesGenerator(
            github_info, self.current_tag, self.last_tag)
        self.assertEqual(generator.github_info, github_info)
        self.assertEqual(generator.current_tag, self.current_tag)
        self.assertEqual(generator.last_tag, self.last_tag)
        self.assertEqual(generator.change_notes.current_tag, self.current_tag)
        self.assertEqual(generator.change_notes._last_tag, self.last_tag)


class TestPublishingGithubReleaseNotesGenerator(unittest.TestCase, GithubApiTestMixin):

    def setUp(self):
        self.init_github()
        self.github_info = {
            'github_owner': 'TestOwner',
            'github_repo': 'TestRepo',
            'github_username': 'TestUser',
            'github_password': 'TestPass',
        }

    @responses.activate
    def test_publish_update_unicode(self):
        tag = 'prod/1.4'
        note = u'“Unicode quotes”'
        self._mock_release(False, tag, True, '')
        # create generator
        generator = self._create_generator(tag)
        # inject content into Changes parser
        generator.parsers[1].content.append(note)
        # render and publish
        content = generator.render()
        release_body = generator.publish(content)
        # verify
        expected_release_body = u'# Changes\r\n\r\n{}'.format(note)
        self.assertEqual(release_body, expected_release_body)
        response_body = json.loads(responses.calls._calls[1].request.body)
        self.assertEqual(response_body['draft'], True)
        self.assertEqual(response_body['prerelease'], False)
        self.assertEqual(len(responses.calls._calls), 2)

    @responses.activate
    def test_publish_update_no_body(self):
        tag = 'prod/1.4'
        self._mock_release(False, tag, True, '')
        # create generator
        generator = self._create_generator(tag)
        # inject content into Changes parser
        generator.parsers[1].content.append('foo')
        # render and publish
        content = generator.render()
        release_body = generator.publish(content)
        # verify
        expected_release_body = '# Changes\r\n\r\nfoo'
        self.assertEqual(release_body, expected_release_body)

    @responses.activate
    def test_publish_update_content_before(self):
        tag = 'prod/1.4'
        self._mock_release(False, tag, True, 'foo\n# Changes\nbar')
        # create generator
        generator = self._create_generator(tag)
        # inject content into parser
        generator.parsers[1].content.append('baz')
        # render and publish
        content = generator.render()
        release_body = generator.publish(content)
        # verify
        self.assertEqual(release_body, 'foo\r\n# Changes\r\n\r\nbaz')

    @responses.activate
    def test_publish_update_content_after(self):
        tag = 'prod/1.4'
        self._mock_release(False, tag, True, '# Changes\nbar\n# Foo\nfoo')
        # create generator
        generator = self._create_generator(tag)
        # inject content into parser
        generator.parsers[1].content.append('baz')
        # render and publish
        content = generator.render()
        release_body = generator.publish(content)
        # verify
        self.assertEqual(release_body, '# Changes\r\n\r\nbaz\r\n\r\n# Foo\r\nfoo')

    @responses.activate
    def test_publish_update_content_before_and_after(self):
        tag = 'prod/1.4'
        self._mock_release(False, tag, True, 'foo\n# Changes\nbar\n# Foo\nfoo')
        # create generator
        generator = self._create_generator(tag)
        # inject content into parser
        generator.parsers[1].content.append('baz')
        # render and publish
        content = generator.render()
        release_body = generator.publish(content)
        # verify
        self.assertEqual(release_body,
            'foo\r\n# Changes\r\n\r\nbaz\r\n\r\n# Foo\r\nfoo')

    @responses.activate
    def test_publish_update_content_between(self):
        tag = 'prod/1.4'
        self._mock_release(False, tag, True,
            '# Critical Changes\nbar\n# Foo\nfoo\n# Changes\nbiz')
        # create generator
        generator = self._create_generator(tag)
        # inject content into parser
        generator.parsers[0].content.append('faz')
        generator.parsers[1].content.append('fiz')
        # render and publish
        content = generator.render()
        release_body = generator.publish(content)
        # verify
        self.assertEqual(release_body,
            '# Critical Changes\r\n\r\nfaz\r\n\r\n' +
            '# Foo\r\nfoo\r\n# Changes\r\n\r\nfiz')

    @responses.activate
    def test_publish_update_content_before_after_and_between(self):
        tag = 'prod/1.4'
        self._mock_release(False, tag, True,
            'goo\n# Critical Changes\nbar\n# Foo\nfoo\n' +
            '# Changes\nbiz\n# Zoo\nzoo')
        # create generator
        generator = self._create_generator(tag)
        # inject content into parser
        generator.parsers[0].content.append('faz')
        generator.parsers[1].content.append('fiz')
        # render and publish
        content = generator.render()
        release_body = generator.publish(content)
        # verify
        self.assertEqual(release_body,
            'goo\r\n# Critical Changes\r\n\r\nfaz\r\n\r\n' +
            '# Foo\r\nfoo\r\n# Changes\r\n\r\nfiz\r\n\r\n' +
            '# Zoo\r\nzoo')

    def _create_generator(self, current_tag, last_tag=None):
        generator = PublishingGithubReleaseNotesGenerator(
            self.github_info.copy(), current_tag, last_tag)
        return generator

    def _mock_release(self, beta, tag, update, body):
        if beta:
            draft = False
            prerelease = True
        else:
            draft = True
            prerelease = False
        # mock the attempted GET of non-existent release
        api_url = '{}/releases/tags/{}'.format(self.repo_api_url, tag)
        if update:
            expected_response = self._get_expected_release(
                body, draft, prerelease)
            status = httplib.OK
        else:
            expected_response = self._get_expected_not_found()
            status = httplib.NOT_FOUND
        responses.add(
            method=responses.GET,
            url=api_url,
            json=expected_response,
            status=status,
        )
        # mock the release creation
        api_url = '{}/releases'.format(self.repo_api_url)
        expected_response = self._get_expected_release(None, draft, prerelease)
        responses.add(
            method=responses.POST,
            url=api_url,
            json=expected_response,
        )
