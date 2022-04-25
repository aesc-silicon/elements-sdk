package elements.soc

import spinal.core._
import spinal.lib._
import spinal.lib.bus.amba3.apb._
import spinal.lib.bus.amba4.axi._

import zibal.misc._
import zibal.platform.Hydrogen
import zibal.board.BoardParameter
import zibal.soc.SocParameter

import nafarr.peripherals.io.gpio.{Apb3Gpio, Gpio, GpioCtrl}
import nafarr.peripherals.com.uart.{Apb3Uart, Uart, UartCtrl}
import nafarr.peripherals.com.spi.{Apb3SpiMaster, Spi, SpiCtrl}
import nafarr.peripherals.com.i2c.{Apb3I2cController, I2c, I2cCtrl}
import nafarr.peripherals.misc.frequencycounter.{
  Apb3FrequencyCounter,
  FrequencyCounter,
  FrequencyCounterCtrl
}
import nafarr.peripherals.io.pio.{Apb3Pio, Pio, PioCtrl}

object HydrogenTest {
  def apply(parameter: Hydrogen.Parameter) = HydrogenTest(parameter)

  case class Parameter(boardParameter: BoardParameter) extends SocParameter(boardParameter, 5) {
    val uartStd = UartCtrl.Parameter.default
    val gpioStatus = GpioCtrl.Parameter(4, 2, (0 to 2), (3 to 3), (3 to 3))
    val gpioA = GpioCtrl.Parameter(32, 2, null, null, null)
    val spiA = SpiCtrl.Parameter.default
    val i2cA = I2cCtrl.Parameter.default
    val freqCounterA = FrequencyCounterCtrl.Parameter.default
    val pioA = PioCtrl.Parameter(2)
  }

  case class HydrogenTest(parameter: Hydrogen.Parameter) extends Hydrogen.Hydrogen(parameter) {
    var socParameter = parameter.getSocParameter.asInstanceOf[Parameter]
    val io_per = new Bundle {
      val uartStd = master(Uart.Io(socParameter.uartStd))
      val gpioStatus = Gpio.Io(socParameter.gpioStatus)
      val gpioA = Gpio.Io(socParameter.gpioA)
      val spiA = master(Spi.Io(socParameter.spiA))
      val i2cA = master(I2c.Io(socParameter.i2cA))
      val freqCounterA = FrequencyCounter.Io(socParameter.freqCounterA)
      val pioA = Pio.Io(socParameter.pioA)
    }

    def prepareZephyr(name: String, elementsConfig: ElementsConfig.ElementsConfig) {
      val dt = ZephyrTools.DeviceTree(elementsConfig, name)
      dt.generate(
        "hydrogentest.dtsi",
        "hydrogen",
        this.system.axiCrossbar.slavesConfigs,
        this.system.apbBridge.io.axi,
        this.apbMapping,
        this.irqMapping
      )
      val board = ZephyrTools.Board(elementsConfig, name)
      board.addLed("heartbeat", this.peripherals.gpioStatusCtrl, 0)
      board.addLed("ok", this.peripherals.gpioStatusCtrl, 1)
      board.addLed("error", this.peripherals.gpioStatusCtrl, 2)
      board.addKey("reset", this.peripherals.gpioStatusCtrl, 3)
      board.generateDeviceTree(this.peripherals.uartStdCtrl)
      board.generateKconfig()
      val cpuClockDomain = this.clockCtrl.getClockDomainByName("system")
      board.generateDefconfig(this.apbMapping, cpuClockDomain)
    }

    val peripherals = new ClockingArea(clockCtrl.getClockDomainByName("system")) {

      val uartStdCtrl = Apb3Uart(socParameter.uartStd)
      uartStdCtrl.io.uart <> io_per.uartStd
      addApbDevice(uartStdCtrl.io.bus, 0x00000, 4 kB)
      addInterrupt(uartStdCtrl.io.interrupt)

      val gpioStatusCtrl = Apb3Gpio(socParameter.gpioStatus)
      gpioStatusCtrl.io.gpio <> io_per.gpioStatus
      addApbDevice(gpioStatusCtrl.io.bus, 0x10000, 4 kB)
      addInterrupt(gpioStatusCtrl.io.interrupt)

      val gpioACtrl = Apb3Gpio(socParameter.gpioA)
      gpioACtrl.io.gpio <> io_per.gpioA
      addApbDevice(gpioACtrl.io.bus, 0x11000, 4 kB)
      addInterrupt(gpioACtrl.io.interrupt)

      val spiMasterACtrl = Apb3SpiMaster(socParameter.spiA)
      spiMasterACtrl.io.spi <> io_per.spiA
      addApbDevice(spiMasterACtrl.io.bus, 0x4000, 4 kB)
      addInterrupt(spiMasterACtrl.io.interrupt)

      val i2cControllerACtrl = Apb3I2cController(socParameter.i2cA)
      i2cControllerACtrl.io.i2c <> io_per.i2cA
      addApbDevice(i2cControllerACtrl.io.bus, 0x50000, 4 kB)
      addInterrupt(i2cControllerACtrl.io.interrupt)

      val frequencyCounterACtrl = Apb3FrequencyCounter(socParameter.freqCounterA)
      frequencyCounterACtrl.io.clock <> io_per.freqCounterA
      addApbDevice(frequencyCounterACtrl.io.bus, 0x60000, 4 kB)

      val pioACtrl = Apb3Pio(socParameter.pioA)
      pioACtrl.io.pio <> io_per.pioA
      addApbDevice(pioACtrl.io.bus, 0x12000, 4 kB)

      connectPeripherals()
    }
  }
}
