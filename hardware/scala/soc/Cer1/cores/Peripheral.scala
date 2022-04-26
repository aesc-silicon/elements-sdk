package elements.soc.cer1

import scala.collection.mutable.ArrayBuffer
import spinal.core._
import spinal.lib._
import spinal.lib.bus.amba3.apb._
import spinal.lib.bus.amba4.axi._
import spinal.lib.bus.misc.SizeMapping
import spinal.lib.com.jtag.Jtag
import nafarr.system.mtimer.{Apb3MachineTimer, MachineTimerCtrl}
import nafarr.system.plic.{Apb3Plic, Plic, PlicCtrl}
import nafarr.peripherals.com.uart.{Apb3Uart, Uart, UartCtrl}
import nafarr.peripherals.io.gpio.{Apb3Gpio, Gpio, GpioCtrl}
import nafarr.networkonchip.amba4.axi._

object Peripheral {
  def apply(parameter: Parameter = Parameter()) = Peripheral(parameter)

  case class Parameter() {
    val gpioA = GpioCtrl.Parameter(8)
    val gpioB = GpioCtrl.Parameter(8)
  }

  case class Io(parameter: Parameter = Parameter()) extends Bundle {
    val gpioA = Gpio.Io(parameter.gpioA)
    val gpioB = Gpio.Io(parameter.gpioB)
  }

  case class Peripheral(parameter: Parameter) extends Component {
    val io = new Bundle {
      val localPort = new Bundle {
        val input = slave(Axi4(axi4Config.coreUpsized))
      }
      val external = new Io(parameter)
    }

    val downsizer = Axi4Downsizer(axi4Config.coreUpsized, axi4Config.coreSmall)
    downsizer.io.input <> io.localPort.input

    /* AXI Subordinates */
    val apbBridge = Axi4SharedToApb3Bridge(
      addressWidth = 20,
      dataWidth = 32,
      idWidth = 4
    )

    /* Generate AXI Crossbar */
    val axiCrossbar = Axi4CrossbarFactory()
    axiCrossbar.addSlave(apbBridge.io.axi, (0x00000000L, 1 MiB))
    axiCrossbar.addConnections(
      downsizer.io.output -> List(apbBridge.io.axi)
    )
    axiCrossbar.build()

    /* Peripheral IP-Cores */
    val apbMapping = ArrayBuffer[(Apb3, SizeMapping)]()
    def addApbDevice(port: Apb3, address: BigInt, size: BigInt) {
      apbMapping += port -> (address, size)
    }

    val gpioACtrl = Apb3Gpio(parameter.gpioA)
    gpioACtrl.io.gpio <> io.external.gpioA
    addApbDevice(gpioACtrl.io.bus, 0x00000, 4 kB)

    val gpioBCtrl = Apb3Gpio(parameter.gpioB)
    gpioBCtrl.io.gpio <> io.external.gpioB
    addApbDevice(gpioBCtrl.io.bus, 0x10000, 4 kB)

    val apbDecoder = Apb3Decoder(
      master = apbBridge.io.apb,
      slaves = apbMapping
    )
  }
}

object PeripheralDemo extends App {
  SpinalVerilog {
    val cd = new ClockingArea(ClockDomain.current.copy(frequency = FixedFrequency(100 MHz))) {
      val top = Peripheral(Peripheral.Parameter())
    }
    cd.top
  }
}
