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
import nafarr.networkonchip.amba4.axi._

object Memory {
  def apply(ramSize: BigInt) = Memory(ramSize)

  case class Memory(ramSize: BigInt) extends Component {
    val io = new Bundle {
      val localPort = new Bundle {
        val input = slave(Axi4(axi4Config.core))
      }
    }

    /* AXI Subordinates */
    val ram = Axi4SharedOnChipRam(
      dataWidth = axi4Config.core.dataWidth,
      byteCount = ramSize,
      idWidth = 4
    )

    /* Generate AXI Crossbar */
    val axiCrossbar = Axi4CrossbarFactory()
    axiCrossbar.addSlave(ram.io.axi, (0x00000000L, 1 MiB))
    axiCrossbar.addConnections(
      io.localPort.input -> List(ram.io.axi)
    )
    axiCrossbar.build()
  }
}

object MemoryDemo extends App {
  SpinalVerilog {
    val cd = new ClockingArea(ClockDomain.current.copy(frequency = FixedFrequency(100 MHz))) {
      val top = Memory(128 KiB)
    }
    cd.top
  }
}
