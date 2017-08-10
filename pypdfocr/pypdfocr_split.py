#!/usr/bin/env python2.7

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



"""
    Try to split pdfs using split pages.
"""

import subprocess
import sys, os
import logging
import glob
import functools
import signal

from multiprocessing import Pool
from pypdfocr_interrupts import init_worker

# Ugly hack to pass in object method to the multiprocessing library
# From http://www.rueckstiess.net/research/snippets/show/ca1d7d90
# Basically gets passed in a pair of (self, arg), and calls the method
def unwrap_self(arg, **kwarg):
    return PySplit._run_split(*arg, **kwarg)



class PySplit(object):
    """Class to run split calls"""
    def __init__(self, config):
        """
           Detect windows tesseract location.  
        """
        self.lang = 'eng'
        self.required = "3.02.02"
        self.threads = config.get('threads',4)
    
        if "binary" in config:  # Override location of binary
            binary = config['binary']
            if os.name == 'nt':
                binary = '"%s"' % binary
                binary = binary.replace("\\", "\\\\")
            logging.info("Setting location for tesseracdt executable to %s" % (binary))
        else:
            if str(os.name) == 'nt':
                # Explicit str here to get around some MagicMock stuff for testing that I don't quite understand
                binary = '"c:\\Program Files (x86)\\Tesseract-OCR\\tesseract.exe"'
            else:
                binary = "tesseract"
    
        self.binary = binary
    
        self.msgs = {
                'TS_MISSING': """ 
                    Could not execute %s
                    Please make sure you have Tesseract installed correctly
                    """ % self.binary,
                        'TS_VERSION':'Tesseract version is too old',
                'TS_img_MISSING':'Cannot find specified tiff file',
                'TS_FAILED': 'Tesseract-OCR execution failed!',
            }        
        
    def _is_version_uptodate(self):
        """
            Make sure the version is current 
        """
        logging.info("Checking tesseract version")
        cmd = '%s -v' % (self.binary)
        logging.info(cmd)        
        try:
            ret_output = subprocess.check_output(cmd, shell=True,  stderr=subprocess.STDOUT)
        except CalledProcessError:
            # Could not run tesseract
            error(self.msgs['TS_MISSING'])

        ver_str = '0.0.0'
        for line in ret_output.splitlines():
            if 'tesseract' in line:
                ver_str = line.split(' ')[1]
                if ver_str.endswith('dev'): # Fix for version strings that end in 'dev'
                    ver_str = ver_str[:-3]

        # Iterate through the version dots
        ver = [int(x) for x in ver_str.split('.')]
        req = [int(x) for x in self.required.split('.')]

        # Aargh, in windows 3.02.02 is reported as version 3.02  
        # SFKM
        if str(os.name) == 'nt':
            req = req[:2]

        version_good = False
        for i,num in enumerate(req):
            if len(ver) < i+1:
                # This minor version number is not present in tesseract, so it must be
                # lower than required.  (3.02 < 3.02.01)
                break
            if ver[i]==num and len(ver) == i+1 and len(ver)==len(req):
                # 3.02.02 == 3.02.02
                version_good = True
                continue
            if ver[i]>num:
                # 4.0 > 3.02.02
                # 3.03.02 > 3.02.02
                version_good = True
                break
            if ver[i]<num:
                # 3.01.02 < 3.02.02
                break
            
        return version_good, ver_str    

    def _warn(self, msg): # pragma: no cover
        print("WARNING: %s" % msg)

    def cmd(self, cmd_list):
        if isinstance(cmd_list, list):
            cmd_list = ' '.join(cmd_list)
        logging.debug("Running cmd: %s" % cmd_list)
        try:
            out = subprocess.check_output(cmd_list, stderr=subprocess.STDOUT, shell=True)
            logging.debug(out)
            return out
        except subprocess.CalledProcessError as e:
            print e.output
            self._warn("Could not run command %s" % cmd_list)
            

    def _run_split(self,  in_filename):
        split_count = 1
        basename, filext = os.path.splitext(in_filename)
        out_filename = '%s_split%d%s' % (basename, split_count, filext)
        
        c = ['convert',
                '"%s"' % in_filename,
                '-respect-parenthesis',
                #'\\( $setcspace -colorspace gray -type grayscale \\)',
                backslash+'(',
                '-clone 0',
                '-colorspace gray -negate -lat 15x15+5% -contrast-stretch 0',
                backslash+') -compose copy_opacity -composite -opaque none +matte -modulate 100,100',
                #'-adaptive-blur 1.0',
                '-blur 1x1',
                #'-selective-blur 4x4+5%',
                '-adaptive-sharpen 0x2',
                '-negate -define morphology:compose=darken -morphology Thinning Rectangle:1x30+0+0 -negate ',  # Removes vertical lines >=60 pixes, reduces widht of >30 (oherwise tesseract < 3.03 completely ignores text close to vertical lines in a table)
                '"%s"' % (out_filename)
                ]
        logging.info("Preprocessing image %s for better OCR" % in_filename)
        res = self.cmd(c)
        if res is None:
            return in_filename
        else:
            return out_filename

    def split(self, in_filenames):
        fns = in_filenames

        pool = Pool(processes=self.threads, initializer=init_worker)
        try:
            logging.info("Starting splitting parallel execution")
            split_filenames = pool.map(unwrap_self,zip([self]*len(fns),fns))
            pool.close()
        except KeyboardInterrupt or Exception:
            print("Caught keyboard interrupt... terminating")
            pool.terminate()
            #sys,exit(-1)
            raise
        finally:
            pool.join()
            logging.info ("Completed splitting")

        return split_filenames




