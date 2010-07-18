
# Makefile.local should define MKHOWTO to point to the Python
# distribution's Doc/tools/mkhowto, e.g.
# MKHOWTO = ${HOME}/cvs/python/dist/src/Doc/tools/mkhowto
include Makefile.local

PAPER=a4
DVIPS=dvips -N0 -t $(PAPER)

html = psycoguide
dvi  = psycoguide.dvi
ps   = psycoguide.ps
ps-gz= psycoguide.ps.gz
all  = $(html) $(dvi) $(ps) $(ps-gz)

html : $(html)
dvi  : $(dvi)
ps   : $(ps)
ps-gz: $(ps-gz)
all  : $(all)

%: %.tex
	-rm -fr $@
	${MKHOWTO} $<

%.dvi: %.tex
	${MKHOWTO} --paper=$(PAPER) --dvi $<

%.ps.gz: %.ps
	gzip -c < $< > $@

%.ps: %.dvi
	$(DVIPS) -o $@ $<

%.pdf: %.tex
	rm -f $*.log $*.out $*.aux
	pdflatex $<
	pdflatex $<
	rm -f $*.log $*.out $*.aux

clean:
	rm -fr $(all)
	rm -f *.log *.aux *.ind *.idx *.l2h *.toc *.syn
