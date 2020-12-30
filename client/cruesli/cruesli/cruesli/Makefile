
# ******
# GENERAL
#

.PHONY: libcruesli client runclient all clean mrproper

all: libcruesli client

mrproper:
	rm -rf build

clean:
	rm -f build/*.o
	rm -rf build/*.dSYM


# ******
# LIBRARY
#


OBJDIR=build
SRCDIR=src

LIB_OBJECTS=$(addprefix $(OBJDIR)/,\
				cruesli.o \
				safe_malloc.o \
				vartable.o \
				www.o \
				util.o)

LIB_LIBS= \
		-lcurl \
		-lpthread \
		-lcjson

LIB_EXPORT_HEADERS=$(addprefix $(SRCDIR)/,\
		libheader.h \
		cscerrs.h \
		entities.h \
		varstructs.h)


libcruesli: $(OBJDIR)/libcruesli.so

$(OBJDIR)/libcruesli.so: $(LIB_OBJECTS) $(LIB_EXPORT_HEADERS)
	cc -g -shared -o $(OBJDIR)/libcruesli.so $(LIB_OBJECTS) $(LIB_LIBS)
	mkdir -p $(OBJDIR)/cruesli
	cp $(LIB_EXPORT_HEADERS) $(OBJDIR)/cruesli
	mv $(OBJDIR)/cruesli/libheader.h $(OBJDIR)/cruesli/cruesli.h


$(OBJDIR)/%.o: $(SRCDIR)/%.c $(SRCDIR)/%.h 
	mkdir -p $(OBJDIR)
	cc -g -c -Wall -Werror -fpic $(filter %.c,$^) -o $@


# ******
# CLIENT
#


CLIENT_FILES=$(addprefix $(SRCDIR)/client/,\
		main.c \
		safe_malloc.c)

CLIENT_HEADERS=$(addprefix $(SRCDIR)/client/,\
		safe_malloc.h)

client: $(OBJDIR)/client


$(OBJDIR)/client: libcruesli $(CLIENT_FILES) $(CLIENT_HEADERS)
	cc -O3 -Lbuild -Ibuild -Wall -Werror  -o $(OBJDIR)/client $(CLIENT_FILES) -lcruesli -lm -lpthread


# ******
# INSTALL
#

install: libcruesli
	cp -r build/cruesli /usr/local/include
	cp -r build/libcruesli.so /usr/local/lib


