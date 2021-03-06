#
# Copyright SAS Institute
#
#  Licensed under the Apache License, Version 2.0 (the License);
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.
#
from __future__ import print_function
from IPython.display import HTML
import IPython.core.magic as ipym
import re
from saspy.SASLogLexer import SASLogStyle, SASLogLexer
from pygments.formatters import HtmlFormatter
from pygments import highlight


@ipym.magics_class
class SASMagic(ipym.Magics):
    """A set of magics useful for interactive work with SAS via saspy
    All the SAS magic cells in a single notebook share a SAS session
    """

    def __init__(self, shell):
        super(SASMagic, self).__init__(shell)
        import saspy as saspy
        self.lst_len = -99  # initialize the length to a negative number to trigger function
        self.mva = saspy.SASsession(kernel=None)
        if self.lst_len < 0:
            self._get_lst_len()

    @ipym.cell_magic
    def SAS(self, line, cell):
        """
        %%SAS - send the code in the cell to a SAS Server

        This cell magic will execute the contents of the cell in a SAS
        session and return any generated output

        Example:
            %%SAS
            proc print data=sashelp.class;
            run;
            data a;
                set sashelp.cars;
            run;
        """
        
        saveOpts="proc optsave out=__jupyterSASKernel__; run;"
        restoreOpts="proc optload data=__jupyterSASKernel__; run;"
        if len(line)>0:  # Save current SAS Options
            self.mva.submit(saveOpts)

        if line.lower()=='smalllog':
            self.mva.submit("options nosource nonotes;")

        elif line is not None and line.startswith('option'):
            self.mva.submit(line + ';')

        res = self.mva.submit(cell)
        dis = self._which_display(res['LOG'], res['LST'])

        if len(line)>0:  # Restore SAS options 
            self.mva.submit(restoreOpts)

        return dis

    @ipym.cell_magic
    def PROC(self,line,cell):
        """
        %%PROC PROCNAME <options>
    	
    	This cell magic will execute the contents of the cell in a SAS session
    	It will send the code the proc given by PROCNAME
    	any options for the proc can be specified after the PROCNAME
    	the magic will not check for missing required options like data= as these differ by proc

	Example 1:
		%%PROC PRINT data=sashelp.cars
		var name age;
		
	Example 2:
		%%PROC IML
		a = I(6); * 6x6 identity matrix;
		b = j(5,5,0); *5x5 matrix of 0's;
		c = j(6,1); *6x1 column vector of 1's;
		d=diag({1 2 4});
		e=diag({1 2, 3 4});
		
	Example 3:
		%%PROC OPTMODEL PRINTLEVEL=2
		/* declare variables */
		var choco >= 0, toffee >= 0;
		
		/* maximize objective function (profit) */
		maximize profit = 0.25*choco + 0.75*toffee;
		
		/* subject to constraints */
		con process1:    15*choco +40*toffee <= 27000;
		con process2:           56.25*toffee <= 27000;
		con process3: 18.75*choco            <= 27000;
		con process4:    12*choco +50*toffee <= 27000;
		/* solve LP using primal simplex solver */
		solve with lp / solver = primal_spx;
		/* display solution */
		print choco toffee;
		
	Example 4:
		%%PROC SQL UNDOPOLICY=NONE
		create table work.class as
		    select * from sashelp.class;
		create table work.class as
		    select sex, avg(age) as age
		    from work.class
		    group by sex;
	"""
        
        saveOpts="proc optsave out=__jupyterSASKernel__; run;"
        restoreOpts="proc optload data=__jupyterSASKernel__; run;"
        
        res = self.mva.submit("proc " + line + ";" + cell + " run; quit;")
        dis = self._which_display(res['LOG'], res['LST'])
        return dis
        
    @ipym.cell_magic
    def IML(self,line,cell):
        """
        %%IML - send the code in the cell to a SAS Server
                for processing by PROC IML

        This cell magic will execute the contents of the cell in a
        PROC IML session and return any generated output. The leading
        PROC IML and trailing QUIT; are submitted automatically.

        Example:
           %%IML
           a = I(6); * 6x6 identity matrix;
           b = j(5,5,0); *5x5 matrix of 0's;
           c = j(6,1); *6x1 column vector of 1's;
           d=diag({1 2 4});
           e=diag({1 2, 3 4});

        """
        res = self.mva.submit("proc iml; " + cell + " quit;")
        dis = self._which_display(res['LOG'], res['LST'])
        return dis

    @ipym.cell_magic
    def OPTMODEL(self, line, cell):
        """
        %%OPTMODEL - send the code in the cell to a SAS Server
                for processing by PROC OPTMODEL

        This cell magic will execute the contents of the cell in a
        PROC OPTMODEL session and return any generated output. The leading
        PROC OPTMODEL and trailing QUIT; are submitted automatically.

        Example:
        proc optmodel;
           /* declare variables */
           var choco >= 0, toffee >= 0;

           /* maximize objective function (profit) */
           maximize profit = 0.25*choco + 0.75*toffee;

           /* subject to constraints */
           con process1:    15*choco +40*toffee <= 27000;
           con process2:           56.25*toffee <= 27000;
           con process3: 18.75*choco            <= 27000;
           con process4:    12*choco +50*toffee <= 27000;
           /* solve LP using primal simplex solver */
           solve with lp / solver = primal_spx;
           /* display solution */
           print choco toffee;
        quit;

        """
        res = self.mva.submit("proc optmodel; " + cell + " quit;")
        dis = self._which_display(res['LOG'], res['LST'])
        return dis

    @ipym.line_magic
    def sasSmallLog(self,line):
        """suppress the notes and source code from the SAS Log for that cell
        The following statements are submitted before and after the code within the cell
        prepend: options nosource nonotes;
        postpend: options source notes;
        :param line: string
        """
        prepend = "options nosource nonotes;"
        postpend = "options source notes;"
        self.code=prepend + self.code + postpend
        return self.code

    @ipym.line_magic
    def sasOptions(self,line):
        """suppress the notes and source code from the SAS Log for that cell
        The following statements are submitted before and after the code within the cell
        prepend: options nosource nonotes;
        postpend: options source notes;
        """
        prepend = "options {0};".format(line)
        self.code=prepend + self.code

        return self.code



    def _get_lst_len(self):
        code="data _null_; run;"
        res = self.mva.submit(code)
        assert isinstance(res, dict)
        self.lst_len=len(res['LST'])
        assert isinstance(self.lst_len,int)
        return

    @staticmethod
    def _which_display(log, output):
        lst_len = 30762
        lines = re.split(r'[\n]\s*', log)
        i = 0
        elog = []
        for line in lines:
            # logger.debug("In lines loop")
            i += 1
            e = []
            if line.startswith('ERROR'):
                e = lines[(max(i - 15, 0)):(min(i + 16, len(lines)))]
            elog = elog + e
        if len(elog) == 0 and len(output) > lst_len:   # no error and LST output
            return HTML(output)
        elif len(elog) == 0 and len(output) <= lst_len:   # no error and no LST
            color_log = highlight(log, SASLogLexer(), HtmlFormatter(full=True, style=SASLogStyle, lineseparator="<br>"))
            return HTML(color_log)
        elif len(elog) > 0 and len(output) <= lst_len:   # error and no LST
            color_log = highlight(log, SASLogLexer(), HtmlFormatter(full=True, style=SASLogStyle, lineseparator="<br>"))
            return HTML(color_log)
        else:   # errors and LST
            color_log = highlight(log, SASLogLexer(), HtmlFormatter(full=True, style=SASLogStyle, lineseparator="<br>"))
            return HTML(color_log + output)


def load_ipython_extension(ipython):
    """Load the extension in Jupyter"""
    ipython.register_magics(SASMagic)


if __name__ == '__main__':
    from IPython import get_ipython

    get_ipython().register_magics(SASMagic)
