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

object Hydrogen1 {
  def apply(parameter: Hydrogen.Parameter) = Hydrogen1(parameter)

  case class Parameter(boardParameter: BoardParameter) extends SocParameter(boardParameter, 2) {
    val uartStd = UartCtrl.Parameter.full
    val gpioStatus = GpioCtrl.Parameter(4, 2, (0 to 2), (3 to 3), (3 to 3))
  }

  case class Hydrogen1(parameter: Hydrogen.Parameter) extends Hydrogen.Hydrogen(parameter) {
    var socParameter = parameter.getSocParameter.asInstanceOf[Parameter]
    val io_per = new Bundle {
      val uartStd = master(Uart.Io(socParameter.uartStd))
      val gpioStatus = Gpio.Io(socParameter.gpioStatus)
    }

    def prepareZephyr(name: String, elementsConfig: ElementsConfig.ElementsConfig) {
      val dt = ZephyrTools.DeviceTree(elementsConfig, name)
      dt.generate(
        "hydrogen1.dtsi",
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
      board.generateDefconfig(this.apbMapping, this.clockCtrl.getClockDomainByName("system"))
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

      connectPeripherals()
    }
  }
}
