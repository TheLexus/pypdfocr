
# Copyright 2013 Virantha Ekanayake All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
import logging
import os
import shutil

import collections
from datetime import datetime
from time import time

from pypdfocr_filer import PyFiler

"""
    Implementation of a filer class 
        -> Works on file system/directory structure
"""
class PyFilerDirs(PyFiler):
    
    def __init__(self):
        self.target_folder = None
        self.default_folder = None
        self.original_move_folder = None
        self.folder_targets = collections.OrderedDict() # use order to have folders at a predictible order
        self.filing_pattern = None     
        self.remove_original = False

    def add_folder_target(self, folder, keywords):
        assert folder not in self.folder_targets, "Target folder already defined! (%s)" % (folder)
        self.folder_targets[folder] = keywords

    def file_original(self, original_filename):
        if not self.original_move_folder:
            if self.original_remove:
                try:
                    os.remove(original_filename)
                    logging.debug("Removed original")
                except:
                    logging.debug("Error removing file %s ...." % original_filename)
                return original_filename                
            else:
                logging.debug("Leaving original untouched")
                return original_filename

        tgt_path = self.original_move_folder
        logging.debug("Moving original %s to %s" % (original_filename, tgt_path))
        tgtfilename = os.path.join(tgt_path, os.path.basename(original_filename))
        tgtfilename = self._get_unique_filename_by_appending_version_integer(tgtfilename)

        shutil.move(original_filename, tgtfilename)
        
        return tgtfilename

    def move_to_matching_folder(self, filename, foldername):
        assert self.target_folder != None
        assert self.default_folder != None
        
        if not foldername:
            logging.info("[DEFAULT] %s --> %s" % (filename, self.default_folder))
            tgt_path = os.path.join(self.target_folder, self.default_folder)
        else:   
            logging.info("[MATCH] %s --> %s" % (filename, foldername))
            tgt_path = os.path.join(self.target_folder,foldername)

        if not os.path.exists(tgt_path):
            logging.debug("Making path %s" % tgt_path)
            os.makedirs(tgt_path)
        
        logging.debug("Moving %s to %s" % (filename, tgt_path))
        
        new_filename = self.create_tgtfilename(filename)        
            
        tgtfilename = os.path.join(tgt_path, os.path.basename(new_filename))
        tgtfilename = self._get_unique_filename_by_appending_version_integer(tgtfilename)

        shutil.move(filename, tgtfilename)
        return tgtfilename

    def create_tgtfilename(self, original_filename):
        # rename file if requested
        if not self.filing_pattern:
            return original_filename
        
        pdf_dir, pdf_basename = os.path.split(original_filename)
        basename = os.path.splitext(pdf_basename)[0]
        
        today = datetime.now()
        now  = today.time()
        
        new_basename = self.filing_pattern.format(filename=basename, day=today.day, month=today.month, year=today.year, hour=now.hour, minute=now.minute, second=now.second)    
        
        return os.path.join(pdf_dir, "%s.pdf" % (new_basename))    
