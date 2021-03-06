from tests.test_actions import *
from ltk.actions.push_action import *
from ltk.actions.clean_action import CleanAction
from ltk.actions.add_action import AddAction
from ltk.actions.rm_action import RmAction
from ltk.actions.request_action import RequestAction
from ltk.actions.download_action import DownloadAction
from io import StringIO
import os
import sys
import unittest
import time

class TestPush(unittest.TestCase):
    def setUp(self):
        create_config()
        self.downloaded = []
        self.add_action = AddAction(os.getcwd())
        self.action = PushAction(self.add_action,os.getcwd(),False,False)#all push_action calls below need to have the kwargs 'due_date' and 'due_reason'.  They aren't declared in the push action itself, but are in the click command that calls the push action when a user uses it and are used in the logic of the push action
        self.clean_action = CleanAction(os.getcwd())
        self.rm_action = RmAction(os.getcwd())
        self.download_action = DownloadAction(os.getcwd())
        self.clean_action.clean_action(True, False, None)
        self.files = ['sample.txt', 'sample1.txt', 'sample2.txt']
        for fn in self.files:
            create_txt_file(fn)
        os.system('ltk add sample*.txt -o') # Let the command line handle parsing the file pattern
        self.doc_ids = self.action.doc_manager.get_doc_ids()
        for doc_id in self.doc_ids:
            assert poll_doc(self.action, doc_id)

    def tearDown(self):
        # delete files added to lingotek cloud
        for curr_file in self.files:
            self.rm_action.rm_action(curr_file, remote=True, force=True)

        # delete downloaded translations
        for df in self.downloaded:
            os.remove(df)

        delete_directory("es-AR")

        self.downloaded = []
        self.clean_action.clean_action(True, False, None)
        self.action.close()
        cleanup()

    def test_push_1(self):
        append_file(self.files[0])
        locales = ['es-AR']
        test_doc_id = self.action.doc_manager.get_doc_by_prop('file_name',self.files[0])['id']
        self.request_action = RequestAction(os.getcwd(), self.files[0], None, locales, False, False, None, None, test_doc_id)
        self.request_action.target_action()
        orig_dates = get_orig_dates(self.action, [test_doc_id]) #get the initial timestamp before modifying the document on the cloud
        assert orig_dates
        self.action.push_action(due_date='', due_reason='')
        assert check_updated_ids(self.action, orig_dates) # Poll and wait until the modification has taken effect in the cloud
        downloaded_path = self.download_action.download_action(test_doc_id, locales[0], False)
        #print("downloaded_path: "+str(downloaded_path))
        self.downloaded.append(downloaded_path)
        with open(downloaded_path, 'r') as f:
            downloaded_text = f.read()
            #print ("Downloaded_text: " + downloaded)

        assert "Texto agregado." in downloaded_text
        assert "Este es un ejemplo de archivo de texto." in downloaded_text

    def test_push_mult(self):
        append_file(self.files[0])
        append_file(self.files[1])
        locales = ['es-AR']
        test_doc_id_0 = self.action.doc_manager.get_doc_by_prop('file_name',self.files[0])['id']
        test_doc_id_1 = self.action.doc_manager.get_doc_by_prop('file_name',self.files[1])['id']
        self.request_action = RequestAction(os.getcwd(), self.files[0], None, locales, False, False, None, None, test_doc_id_0)
        target1 = self.request_action.target_action()
        self.request_action = RequestAction(os.getcwd(), self.files[1], None, locales, False, False, None, None, test_doc_id_1)
        target2 = self.request_action.target_action()
        orig_dates = get_orig_dates(self.action, [test_doc_id_0, test_doc_id_1]) #get the initial timestamp before modifying the document on the cloud
        assert orig_dates
        push = self.action.push_action(due_date='', due_reason='')
        assert check_updated_ids(self.action, orig_dates) # Poll and wait until the modification has taken effect on the cloud
        dl_path_0 = self.download_action.download_action(test_doc_id_0, locales[0], False)
        dl_path_1 = self.download_action.download_action(test_doc_id_1, locales[0], False)
        self.downloaded = [dl_path_0, dl_path_1]
        for path in self.downloaded:
            with open(path, 'r') as f:
                downloaded_text = f.read()
                #print("downloaded_text: "+downloaded_text)

            assert "Texto agregado." in downloaded_text
            assert "Este es un ejemplo de archivo de texto." in downloaded_text

    def test_push_none(self):
        try:
            # out = StringIO()
            # sys.stdout = out
            assert not self.action.push_action(due_date='', due_reason='')
            # info = out.getvalue()
            # assert 'All documents up-to-date with Lingotek Cloud.' in info
        finally:
            sys.stdout = sys.__stdout__

    def test_push_dry_run(self):
        append_file(self.files[0])
        append_file(self.files[1])
        locales = ['es-AR']
        test_doc_id_0 = self.action.doc_manager.get_doc_by_prop('file_name',self.files[0])['id']
        test_doc_id_1 = self.action.doc_manager.get_doc_by_prop('file_name',self.files[1])['id']
        self.request_action = RequestAction(os.getcwd(), self.files[0], None, locales, False, False, None, None, test_doc_id_0)
        target1 = self.request_action.target_action()
        self.request_action = RequestAction(os.getcwd(), self.files[1], None, locales, False, False, None, None, test_doc_id_1)
        target2 = self.request_action.target_action()
        orig_dates = get_orig_dates(self.action, [test_doc_id_0, test_doc_id_1]) #get the initial timestamp before modifying the document on the cloud
        assert orig_dates
        try:
            out = StringIO()
            sys.stdout = out
            self.action.test = True
            handler = logging.StreamHandler(sys.stdout)
            handler.setLevel(logging.INFO)
            formatter = logging.Formatter('%(message)s')
            handler.setFormatter(formatter)
            logger.addHandler(handler)
            push = self.action.push_action(due_date='', due_reason='')
            info = out.getvalue()
            assert 'Update '+self.files[0] in info
            assert 'Update '+self.files[1] in info
            assert 'TEST RUN: Added 0, Updated 2 (Total 2)' in info
            logger.removeHandler(handler)
        finally:
            sys.stdout = sys.__stdout__
        print("polling to check that file wasn't modified.  This will take 6 minutes if successful.")
        assert not check_updated_ids(self.action, orig_dates) # Poll and wait to make sure the modification didn't occur on the cloud
        dl_path_0 = self.download_action.download_action(test_doc_id_0, locales[0], False)
        dl_path_1 = self.download_action.download_action(test_doc_id_1, locales[0], False)
        self.downloaded = [dl_path_0, dl_path_1]
        for path in self.downloaded:
            with open(path, 'r') as f:
                downloaded_text = f.read()
                #print("downloaded_text: "+downloaded_text)

            assert "Texto agregado." not in downloaded_text
            assert "Este es un ejemplo de archivo de texto." in downloaded_text

    def test_push_title(self):
        dir_path = os.path.join(os.getcwd(), 'nested')
        nestedfile = 'nested'+os.sep+'nestedfile.txt'
        create_directory(dir_path)
        create_txt_file(nestedfile)
        os.system('ltk add nested'+os.sep+'nestedfile.txt -o')
        append_file(self.files[0])
        append_file(nestedfile)
        locales = ['es-AR']
        test_doc_id_0 = self.action.doc_manager.get_doc_by_prop('file_name',self.files[0])['id']
        test_doc_id_1 = self.action.doc_manager.get_doc_by_prop('file_name',nestedfile)['id']
        self.request_action = RequestAction(os.getcwd(), self.files[0], None, locales, False, False, None, None, test_doc_id_0)
        target1 = self.request_action.target_action()
        self.request_action = RequestAction(os.getcwd(), nestedfile, None, locales, False, False, None, None, test_doc_id_1)
        target2 = self.request_action.target_action()
        orig_dates = get_orig_dates(self.action, [test_doc_id_0, test_doc_id_1]) #get the initial timestamp before modifying the document on the cloud
        assert orig_dates
        try:
            out = StringIO()
            sys.stdout = out
            self.action.title = True
            handler = logging.StreamHandler(sys.stdout)
            handler.setLevel(logging.INFO)
            formatter = logging.Formatter('%(message)s')
            handler.setFormatter(formatter)
            logger.addHandler(handler)
            push = self.action.push_action(due_date='', due_reason='')
            info = out.getvalue()
            assert 'Updated '+self.files[0] in info
            assert 'Updated nestedfile.txt' in info #should be just nestedfile.txt, not nested/nestedfile.txt
            logger.removeHandler(handler)
        finally:
            sys.stdout = sys.__stdout__
        assert check_updated_ids(self.action, orig_dates) # Poll and wait until the modification has taken effect on the cloud
        dl_path_0 = self.download_action.download_action(test_doc_id_0, locales[0], False)
        dl_path_1 = self.download_action.download_action(test_doc_id_1, locales[0], False)
        self.downloaded = [dl_path_0, dl_path_1]
        for path in self.downloaded:
            with open(path, 'r') as f:
                downloaded_text = f.read()
                #print("downloaded_text: "+downloaded_text)

            assert "Texto agregado." in downloaded_text
            assert "Este es un ejemplo de archivo de texto." in downloaded_text

        self.rm_action.rm_action(nestedfile, remote=True, force=True)
        delete_directory("nested")

    def test_push_metadata(self):
        from unittest.mock import patch
        with patch('builtins.input', side_effect = ['alpha','beta','','','','','','','','','','','','','','','','','','','','','','','','','','','','','','','','','','','','','','','','','','','']):
            self.action.push_action(set_metadata=True, due_date='', due_reason='')
        #check that the metadata is attached to the documents
        for doc_id in self.action.doc_manager.get_doc_ids():
            properties = self.action.api.get_document(doc_id).json()['properties']
            for field in METADATA_FIELDS:
                if field == METADATA_FIELDS[0]:
                    assert field in properties
                    assert properties[field]== 'alpha'
                elif field == METADATA_FIELDS[1]:
                    assert field in properties
                    assert properties[field] == 'beta'
                else:
                    #for some reason, the PATCH call adds some False or None values where metadata wasn't set.  Values are kept if they are set, so everything works, we just need to check for fields that are returned that we didn't set.
                    if field == 'require_review':
                        assert not properties['require_review'] #should be False because it was set to an empty string
                        continue
                    if field == 'external_url':
                        assert not properties['require_review'] #should be None because it was set to an empty string
                        continue
                    assert field not in properties

        #modify the metadata
        with patch('builtins.input', side_effect = ['','delta','gamma','','','','','','','','','','','','','','','','','','','','','','','','','','','','','','','','','','','','','','','','','','']):
            self.action.push_action(set_metadata=True, due_date='', due_reason='')


        #check that the metadata was updated
        for doc_id in self.action.doc_manager.get_doc_ids():
            properties = self.action.api.get_document(doc_id).json()['properties']
            for field in METADATA_FIELDS:
                if field == METADATA_FIELDS[0]:
                    assert field in properties
                    assert properties[field]== 'alpha'
                elif field == METADATA_FIELDS[1]:
                    assert field in properties
                    assert properties[field] == 'delta'
                elif field == METADATA_FIELDS[2]:
                    assert field in properties
                    assert properties[field] == 'gamma'
                else:
                    if field == 'require_review': #for some reason, the PATCH call adds some False or None values where metadata wasn't set.  Values are kept if they are set, so everything works, we just need to check for fields that are returned that we didn't set.
                        assert not properties['require_review'] #should be False because it was set to an empty string
                        continue
                    if field == 'external_url':
                        assert not properties['require_review'] #should be None because it was set to an empty string
                        continue
                    assert field not in properties

    def test_push_default_metadata(self):
        #set default metadata directly so the config action can be tested in its own unit test
        self.action.default_metadata[METADATA_FIELDS[2]] = "delta"
        self.action.default_metadata[METADATA_FIELDS[3]] = "gamma"
        
        self.action.push_action(due_date='', due_reason='')

        #check that the metadata is attached to the documents
        for doc_id in self.action.doc_manager.get_doc_ids():
            properties = self.action.api.get_document(doc_id).json()['properties']
            for field in METADATA_FIELDS:
                if field == METADATA_FIELDS[2]:
                    assert field in properties
                    assert properties[field]== 'delta'
                elif field == METADATA_FIELDS[3]:
                    assert field in properties
                    assert properties[field] == 'gamma'
                else:
                    if field == 'require_review': #for some reason, the PATCH call adds some False or None values where metadata wasn't set.  Values are kept if they are set, so everything works, we just need to check for fields that are returned that we didn't set.
                        assert not properties['require_review'] #should be False because it was set to an empty string
                        continue
                    if field == 'external_url':
                        assert not properties['require_review'] #should be None because it was set to an empty string
                        continue
                    assert field not in properties

    def test_push_named(self):
        append_file(self.files[0])
        append_file(self.files[1])
        locales = ['es-AR']
        test_doc_id_0 = self.action.doc_manager.get_doc_by_prop('file_name',self.files[0])['id']
        test_doc_id_1 = self.action.doc_manager.get_doc_by_prop('file_name',self.files[1])['id']
        self.request_action = RequestAction(os.getcwd(), self.files[0], None, locales, False, False, None, None, test_doc_id_0)
        target1 = self.request_action.target_action()
        self.request_action = RequestAction(os.getcwd(), self.files[1], None, locales, False, False, None, None, test_doc_id_1)
        target2 = self.request_action.target_action()
        orig_dates0 = get_orig_dates(self.action, [test_doc_id_0]) #get the initial timestamp before modifying the document on the cloud
        assert orig_dates0
        orig_dates1 = get_orig_dates(self.action, [test_doc_id_1]) #get the initial timestamp before modifying the document on the cloud
        assert orig_dates1
        push = self.action.push_action(files=[self.files[0]], due_date='', due_reason='')
        assert check_updated_ids(self.action, orig_dates0) # Poll and wait until the modification has taken effect on the cloud
        print("polling to check that file wasn't modified.  This will take 3 minutes if successful.")
        assert not check_updated_ids(self.action, orig_dates1) # Poll and wait to make sure the modification didn't occur on the cloud
        dl_path_0 = self.download_action.download_action(test_doc_id_0, locales[0], False)
        dl_path_1 = self.download_action.download_action(test_doc_id_1, locales[0], False)
        self.downloaded = [dl_path_0, dl_path_1]
        with open(dl_path_0, 'r') as f:
            downloaded_text = f.read()
            #print("downloaded_text: "+downloaded_text)
        assert "Texto agregado." in downloaded_text, downloaded_text
        assert "Este es un ejemplo de archivo de texto." in downloaded_text, downloaded_text
        with open(dl_path_1, 'r') as f:
            downloaded_text = f.read()
            #print("downloaded_text: "+downloaded_text)
        assert "Texto agregado." not in downloaded_text, downloaded_text
        assert "Este es un ejemplo de archivo de texto." in downloaded_text, downloaded_text

    def test_push_metadata_only(self):
        append_file(self.files[0])
        locales = ['es-AR']
        test_doc_id = self.action.doc_manager.get_doc_by_prop('file_name',self.files[0])['id']
        self.request_action = RequestAction(os.getcwd(), self.files[0], None, locales, False, False, None, None, test_doc_id)
        self.request_action.target_action()
        orig_dates = get_orig_dates(self.action, [test_doc_id]) #get the initial timestamp before modifying the document on the cloud
        assert orig_dates
        from unittest.mock import patch
        with patch('builtins.input', side_effect = ['alpha','beta','','','','','','','','','','','','','','','','','','','','','','','','','','','','','','','','','','','','','','','','','','','']):
            self.action.push_action(set_metadata=True, metadata_only=True, due_date='', due_reason='')

        #check that the file contents weren't updated
        print("polling to check that file wasn't modified.  This will take 3 minutes if successful.")
        assert not check_updated_ids(self.action, orig_dates) # Poll and wait to make sure the modification didn't occur on the cloud
        downloaded_path = self.download_action.download_action(test_doc_id, locales[0], False)
        #print("downloaded_path: "+str(downloaded_path))
        self.downloaded.append(downloaded_path)
        with open(downloaded_path, 'r') as f:
            downloaded_text = f.read()
            #print ("Downloaded_text: " + downloaded)
        assert "Texto agregado." not in downloaded_text
        assert "Este es un ejemplo de archivo de texto." in downloaded_text

        #check that the metadata was updated
        for doc_id in self.action.doc_manager.get_doc_ids():
            properties = self.action.api.get_document(doc_id).json()['properties']
            for field in METADATA_FIELDS:
                if field == METADATA_FIELDS[0]:
                    assert field in properties
                    assert properties[field]== 'alpha'
                elif field == METADATA_FIELDS[1]:
                    assert field in properties
                    assert properties[field] == 'beta'
                else:
                    if field == 'require_review': #for some reason, the PATCH call adds some False or None values where metadata wasn't set.  Values are kept if they are set, so everything works, we just need to check for fields that are returned that we didn't set.
                        assert not properties['require_review'] #should be False because it was set to an empty string
                        continue
                    if field == 'external_url':
                        assert not properties['require_review'] #should be None because it was set to an empty string
                        continue
                    assert field not in properties
        
#don't need tests for pushing to cancelled documents, because push only works for tracked documents and cancelled documents are never tracked.  Someone would have to intentionally try and break this by editing the docs.json file, at which point they're asking for errors.
