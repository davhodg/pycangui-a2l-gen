/* SPDX-License-Identifier: Apache-2.0 */
/* SPDX-FileCopyrightText: 2026 davhodg */
/* The program the tests build A2Ls from (demo.elf, by gcc -g -O0): a few
   variables of the kinds an ECU has, named so a regular expression picks
   measurements and characteristics apart. */

#include <stdint.h>

typedef struct
{
    uint16_t speed;
    int16_t  torque;
    float    temperature;
} motor_t;

volatile uint16_t meas_battery_mv;
volatile int32_t  meas_position;
volatile float    meas_current_a;
volatile motor_t  meas_motor;
volatile uint8_t  meas_flags[4];

volatile uint16_t cal_speed_limit = 3000U;
volatile float    cal_gain = 1.5F;
volatile int16_t  cal_table[8] = { 0, 1, 2, 3, 4, 5, 6, 7 };

int main( void )
{
    meas_battery_mv = cal_speed_limit;
    meas_current_a = cal_gain * (float)cal_table[3];
    meas_motor.speed = meas_battery_mv;
    meas_position = meas_motor.torque + (int32_t)meas_flags[0];
    return 0;
}
