package elements.soc

import spinal.core._
import spinal.lib._

import nafarr.networkonchip.amba4.axi._
import nafarr.peripherals.com.chip2chip._

import elements.soc.cer1._

object Cer1 {
  def apply() = new Cer1()

  case class Cer1() extends Component {
    val io = new Bundle {
      val systemController = new SystemController.Io()
      val computingA = new Computing.Io()
      val computingB = new Computing.Io()
      val peripheralA = new Peripheral.Io()
    }

    val chipletSystemController = new Area {
      val core =
        SystemController.SystemControllerWithMemory(32 KiB, 64 KiB, SystemController.Parameter())
      io.systemController <> core.io.external

      val extension = Axi4MemoryExtension(axi4Config.coreUpsized, axi4Config.core, apb3Config, 1)
      val localPort =
        Axi4LocalPort(axi4Config.noc, axi4Config.core, apb3Config, true, false, 4, false)
      val router = Axi4Router(axi4Config.noc, apb3Config, 2, 2)
      localPort.io.bus.router <> router.io.bus
      localPort.io.bus.extension <> extension.io.bus

      router.io.local.output >> localPort.io.local.input
      localPort.io.core.output >> extension.io.fromNoc.input
      extension.io.fromNoc.output >> core.io.localPort.input

      core.io.localPort.output >> extension.io.fromCore.input
      extension.io.fromCore.output >> localPort.io.core.input
      localPort.io.local.output >> router.io.local.input
    }

    val chipletComputingA = new Area {
      val core = Computing(4 KiB)
      io.computingA <> core.io.external

      val translation = Axi4MemoryTranslation(axi4Config.core, apb3Config, 4)
      val extension = Axi4MemoryExtension(axi4Config.coreUpsized, axi4Config.core, apb3Config, 2)
      val localPort = Axi4LocalPort(axi4Config.noc, axi4Config.core, apb3Config, true, true, 1)
      val router = Axi4Router(axi4Config.noc, apb3Config, 2, 2)
      localPort.io.bus.router <> router.io.bus
      localPort.io.bus.extension <> extension.io.bus
      localPort.io.bus.translation <> translation.io.bus

      router.io.local.output >> localPort.io.local.input
      localPort.io.core.output >> extension.io.fromNoc.input
      extension.io.fromNoc.output >> core.io.localPort.input

      core.io.localPort.output >> extension.io.fromCore.input
      extension.io.fromCore.output >> translation.io.input
      translation.io.output >> localPort.io.core.input
      localPort.io.local.output >> router.io.local.input
    }

    val chipletComputingB = new Area {
      val core = Computing(4 KiB)
      io.computingB <> core.io.external

      val translation = Axi4MemoryTranslation(axi4Config.core, apb3Config, 4)
      val extension = Axi4MemoryExtension(axi4Config.coreUpsized, axi4Config.core, apb3Config, 2)
      val localPort = Axi4LocalPort(axi4Config.noc, axi4Config.core, apb3Config, true, true, 1)
      val router = Axi4Router(axi4Config.noc, apb3Config, 2, 2)
      localPort.io.bus.router <> router.io.bus
      localPort.io.bus.extension <> extension.io.bus
      localPort.io.bus.translation <> translation.io.bus

      router.io.local.output >> localPort.io.local.input
      localPort.io.core.output >> extension.io.fromNoc.input
      extension.io.fromNoc.output >> core.io.localPort.input

      core.io.localPort.output >> extension.io.fromCore.input
      extension.io.fromCore.output >> translation.io.input
      translation.io.output >> localPort.io.core.input
      localPort.io.local.output >> router.io.local.input
    }

    val chipletPeripheralA = new Area {
      val core = Peripheral()
      io.peripheralA <> core.io.external

      val plug = Axi4Plugs.Subordinate(axi4Config.core)
      val extension = Axi4MemoryExtension(axi4Config.coreUpsized, axi4Config.core, apb3Config, 4)
      val localPort = Axi4LocalPort(axi4Config.noc, axi4Config.core, apb3Config, true, false, 4)
      val router = Axi4Router(axi4Config.noc, apb3Config, 2, 2)
      localPort.io.bus.router <> router.io.bus
      localPort.io.bus.extension <> extension.io.bus

      router.io.local.output >> localPort.io.local.input
      localPort.io.core.output >> extension.io.fromNoc.input
      extension.io.fromNoc.output >> core.io.localPort.input

      plug.io.output >> extension.io.fromCore.input
      extension.io.fromCore.output >> localPort.io.core.input
      localPort.io.local.output >> router.io.local.input
    }

    val connections = List(
      (chipletSystemController.router.io.east, chipletComputingA.router.io.west, 1),
      (chipletComputingA.router.io.east, chipletComputingB.router.io.west, 1),
      (chipletComputingA.router.io.north, chipletPeripheralA.router.io.south, 1)
    )

    for ((portA, portB, phyCount) <- connections) {
      val interfaceA = Interface.Axi4Interface(axi4Config.noc, phyCount)
      interfaceA.io.axiIn <> portA.output
      interfaceA.io.axiOut <> portA.input
      val interfaceB = Interface.Axi4Interface(axi4Config.noc, phyCount)
      interfaceB.io.axiIn <> portB.output
      interfaceB.io.axiOut <> portB.input

      for (index <- 0 until interfaceA.phyCount) {
        interfaceA.io.txPhy(index) >> interfaceB.io.rxPhy(index)
        interfaceA.io.rxPhy(index) << interfaceB.io.txPhy(index)
      }
    }

    val plugs = List(
      chipletSystemController.router.io.north,
      chipletSystemController.router.io.south,
      chipletSystemController.router.io.west,
      chipletComputingA.router.io.south,
      chipletComputingB.router.io.north,
      chipletComputingB.router.io.east,
      chipletComputingB.router.io.south,
      chipletPeripheralA.router.io.north,
      chipletPeripheralA.router.io.east,
      chipletPeripheralA.router.io.west
    )

    for (port <- plugs) {
      Axi4Plugs.Router(axi4Config.noc, port.input, port.output)
    }
  }
}
