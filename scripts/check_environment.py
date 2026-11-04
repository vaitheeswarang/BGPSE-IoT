import sys,platform,numpy,pandas,PIL,cryptography,scipy,matplotlib
print('Python',sys.version.replace('\n',' ')); print('OS',platform.platform()); print('CPU',platform.processor());
for m in [numpy,pandas,PIL,cryptography,scipy,matplotlib]: print(m.__name__,getattr(m,'__version__','n/a'))
