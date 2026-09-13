// Assign SPI0 -- the Cirque is wired to GP2/GP3/GP4 (SPI0 SCK/TX/RX).
#pragma once

#include_next <mcuconf.h>

#undef RP_SPI_USE_SPI0
#define RP_SPI_USE_SPI0 TRUE
