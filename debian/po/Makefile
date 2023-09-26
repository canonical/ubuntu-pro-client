all: build

POS=$(wildcard *.po)
MOS=$(POS:.po=.mo)

%.mo: %.po
	mkdir -p usr/share/locale/$*/LC_MESSAGES
	msgfmt $< -o usr/share/locale/$*/LC_MESSAGES/ubuntu-pro.mo

build: $(MOS)
