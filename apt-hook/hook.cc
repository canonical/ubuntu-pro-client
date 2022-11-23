/*
 * Copyright (C) 2018-2019 Canonical Ltd
 * Author: Julian Andres Klode <juliank@ubuntu.com>
 *
 * This program is free software: you can redistribute it and/or modify
 * it under the terms of the GNU General Public License as published by
 * the Free Software Foundation, version 3 of the License.
 *
 * This package is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License
 * along with this program. If not, see <https://www.gnu.org/licenses/>.
 *
*/

#include <libintl.h>
#include <locale.h>

#include "esm-templates.hh"

int main(int argc, char *argv[])
{
   (void) argc;   // unused
   (void) argv;   // unused

   setlocale(LC_ALL, "");
   textdomain("ubuntu-advantage");

   process_all_templates();

   return 0;
}
