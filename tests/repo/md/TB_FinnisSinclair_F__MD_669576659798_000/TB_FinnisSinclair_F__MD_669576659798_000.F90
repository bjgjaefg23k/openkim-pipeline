

#include "KIM_API_status.h"
#define THIS_FILE_NAME "HELP"


    module TB_FinnisSinclair
!---^^^^^^^^^^^^^^^^^^^^^^^^
!*      An implementation of the second moment approximation
!*      interatomic potential due to Finnis and Sinclair
!*
!*          A simple empirical N-body potential for transition metals
!*
!*          M. W. Finnis and J. E. Sinclair
!*          Philosophical Magazine A, 50: 1, 45 — 55 (1984)
!*
!*
!*          A simple form of multi-ion interaction has been constructed for the purpose of
!*          atomistic simulation of transition metals. The model energy consists of a bonding
!*          term, which is the square-root of a site density rho_i, summed over atoms i, and a repulsive
!*          pairwise term of the form sum_ij 1/2 V(R_ij). The site density rho_i is defined as a
!*          sum over neighbouring sites j of a cohesive potential phi(R_ij). Both V and phi are
!*          assumed to be short-ranged and are parameterized to fit the lattice constant,
!*          cohesive energy and elastic moduli of the seven body-centred-cubic (b.c.c.) transition
!*          metals. The result is a simple model which, unlike a pair-potential model,
!*          can account for experimental vacancy-formation energies and does not require an
!*          externally applied pressure to balance the 'Cauchy pressure'.
!*
!*          NOTE: see also PHILOSOPHICAL MAGAZINE, 1986, VOL. 53, NO. 1, 161 for erratum
!*
!*      author      :   Daniel Mason
!*      revision    :   14/3/2012
!*      version     :   1.0
!*
!*      This version is stripped down and retooled for KIM
!*
!*
!*
!*

        use KIM_API
        implicit none
        private

    !---    KIM API

        public      ::      Compute_Energy_Forces_FS
        public      ::      Destroy_FS

    !---

        public      ::      FinnisSinclair_ctor
        public      ::      report
        public      ::      delete

        public      ::      getA
        public      ::      getd
        public      ::      getbeta
        public      ::      getc
        public      ::      getc0
        public      ::      getc1
        public      ::      getc2


    !---    Member Functions

        public      ::      ionicPotentialEnergy
        public      ::      addForce
        public      ::      getCutoff

    !---    for ease of extending the Finnis-Sinclair model ( take care... )
        public      ::      cohesivePairPotential
        public      ::      dcohesivePairPotential
        public      ::      repulsivePairPotential
        public      ::      drepulsivePairPotential
        public      ::      bandEnergy
        public      ::      dbandEnergy

    !---


        type,public     ::      FinnisSinclair
            private
        !---    these parameters are from the original Finnis-Sinclair potential
            real(kind=8)          ::      A           !   band energy scale
            real(kind=8)          ::      d           !   density cut-off range
            real(kind=8)          ::      betaond     !   note: beta by itself is not used.
            real(kind=8)          ::      c           !   pair potential cut-off
            real(kind=8)          ::      c0,c1,c2    !   pair potential polynomial coefficients

        end type

    !---



        interface   FinnisSinclair_ctor
            module procedure        FinnisSinclair_null
            module procedure        FinnisSinclair_ctor0
        end interface FinnisSinclair_ctor

        interface   report
            module procedure        report0
        end interface

        interface   delete
            module procedure        delete0
        end interface


        interface ionicPotentialEnergy
            module procedure    FinnisSinclair_atomic1
        end interface

        interface getCutoff
           module procedure     getCutoffFinnisSinclair
        end interface


        interface addForce
            module procedure    addForceFinnisSinclair1
            module procedure    addForceFinnisSinclair2
        end interface


        interface bandEnergy
           module procedure     bandEnergy0
        end interface

        interface dbandEnergy
           module procedure     dbandEnergy0
        end interface


        interface cohesivePairPotential
           module procedure     cohesivePairPotential0
        end interface

        interface dcohesivePairPotential
           module procedure     dcohesivePairPotential0
        end interface

        interface repulsivePairPotential
           module procedure     repulsivePairPotential0
        end interface

        interface drepulsivePairPotential
           module procedure     drepulsivePairPotential0
        end interface


    contains
!---^^^^^^^^

        function FinnisSinclair_null( ) result(this)
    !---^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
    !       null constructor for Finnis-Sinclair potential - returns the
    !       Tungsten model from the original paper.
            type(FinnisSinclair)    ::      this
            this = FinnisSinclair_ctor0( 1.887117d0,4.114825d0,0.0d0,3.25d0,    &
                                        47.1346499d0,-33.7665665d0,6.2541999d0 )
            return
        end function FinnisSinclair_null


        function FinnisSinclair_ctor0( A,beta,d,c,c0,c1,c2 ) result(this)
    !---^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
    !       default constructor for FinnisSinclair potential
            real(kind=8),intent(in)         ::      A,beta,d,c,c0,c1,c2
            type(FinnisSinclair)    ::      this

            this%A = A
            this%d = d
            this%betaond = beta/d
            this%c = c
            this%c0 = c0
            this%c1 = c1
            this%c2 = c2

            return
        end function FinnisSinclair_ctor0

        subroutine report0( this,u )
    !---^^^^^^^^^^^^^^^^^^^^^^^^^^^^
            type(FinnisSinclair),intent(in)     ::      this
            integer,intent(in),optional         ::      u
            integer         ::      uu
            uu = 6
            if (present(u)) uu = u
            write (unit=uu,fmt='(a)') "FinnisSinclair"
            write (unit=uu,fmt='(a,3f16.8)') "    (A,d,beta)   = ",this%A,this%d,this%betaond*this%d
            write (unit=uu,fmt='(a,4f16.8)') "    (c,c0,c1,c2) = ",this%c,this%c0,this%c1,this%c2
            return
        end subroutine report0

        subroutine delete0( this )
    !---^^^^^^^^^^^^^^^^^^^^^^^^^^
    !*      deallocate dynamic memory: none used so this routine does nothing
            type(FinnisSinclair),intent(inout)      ::      this
            return
        end subroutine delete0

!-------

        pure function bandEnergy0( this,rho ) result( E )
    !---^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
    !*      compute the band energy from the electron density
            type(FinnisSinclair),intent(in) ::      this
            real(kind=8),intent(in)                 ::      rho
            real(kind=8)                          ::      E
            if (rho > 0) then
                E = - this%A * sqrt( rho )
            else
                E = 0.0
            end if
            return
        end function bandEnergy0

        subroutine dbandEnergy0( this,rho, E,dEdrho )
    !---^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
    !*      compute the band energy from the electron density
    !*      and its derivative with respect to density
            type(FinnisSinclair),intent(in) ::      this
            real(kind=8),intent(in)                 ::      rho
            real(kind=8),intent(out)                ::      E
            real(kind=8),intent(out)                ::      dEdrho
            if (rho > 0) then
                E       = sqrt( rho )             !   use this as a dummy for now...
                dEdrho  = -0.5*this%A/E
                E       = -this%A*E
            else
                E       = 0.0
                dEdrho  = 0.0               !   this may seem odd, but it should be ok as drho/dr = 0 at rho=0.
            end if
            return
        end subroutine dbandEnergy0

        subroutine d2bandEnergy( this,rho, E,dEdrho,d2Edrho2 )
    !---^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
    !*      compute the band energy from the electron density
    !*      and its derivatives with respect to density
            type(FinnisSinclair),intent(in) ::      this
            real(kind=8),intent(in)                 ::      rho
            real(kind=8),intent(out)                ::      E
            real(kind=8),intent(out)                ::      dEdrho,d2Edrho2
            if (rho > 0) then
                E       = sqrt( rho )             !   use this as a dummy for now...
                dEdrho  = -0.5*this%A/E
                d2Edrho2 = 0.25*this%A/(E*rho)
                E       = -this%A*E
            else
                E       = 0.0
                dEdrho  = 0.0               !   this may seem odd, but it should be ok as drho/dr = 0 at rho=0.
                d2Edrho2 = 0.0
            end if
            return
        end subroutine d2bandEnergy

    !---

        pure function repulsivePairPotential0( this,r ) result( V )
    !---^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
    !*      returns the repulsive pair potential V(r) ( eqn 28 )
            type(FinnisSinclair),intent(in)     ::      this
            real(kind=8),intent(in)                     ::      r
            real(kind=8)                              ::      V
            if (r < this%c) then
                V = ( r - this%c )*( r - this%c )*( this%c0 + r*(this%c1 + r*this%c2) )
            else
                V = 0.0
            end if
            return
        end function repulsivePairPotential0

        pure subroutine drepulsivePairPotential0( this,r , V,dVdr )
    !---^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
    !*      returns the repulsive pair potential V(r) ( eqn 28 )
    !*      and its derivative wrt r
            type(FinnisSinclair),intent(in)     ::      this
            real(kind=8),intent(in)                   ::      r
            real(kind=8),intent(out)                  ::      V,dVdr
            if (r < this%c) then
                V = ( r - this%c )*( r - this%c )*( this%c0 + r*(this%c1 + r*this%c2) )
                dVdr = ( r - this%c )*( 2*( this%c0 + r*(this%c1 + r*this%c2) )             &
                                      +( r - this%c )*( this%c1 + r*2*this%c2) )
            else
                V    = 0.0
                dVdr = 0.0
            end if
            return
        end subroutine drepulsivePairPotential0

        pure subroutine d2repulsivePairPotential( this,r , V,dVdr,d2Vdr2 )
    !---^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
    !*      returns the repulsive pair potential V(r) ( eqn 28 )
    !*      and its derivatives wrt r
            type(FinnisSinclair),intent(in)     ::      this
            real(kind=8),intent(in)                   ::      r
            real(kind=8),intent(out)                  ::      V,dVdr,d2Vdr2
            if (r < this%c) then
                V = ( r - this%c )*( r - this%c )*( this%c0 + r*(this%c1 + r*this%c2) )
                dVdr = ( r - this%c )*( 2*( this%c0 + r*(this%c1 + r*this%c2) )             &
                                      +( r - this%c )*( this%c1 + r*2*this%c2) )
                d2Vdr2 = 2*( this%c0 + r*(this%c1 + r*this%c2) )                            &
                       + 2*( r - this%c )*( (this%c1 + 2*r*this%c2) )                       &
                       + ( r - this%c )*( r - this%c )*( 2*this%c2 )
            else
                V    = 0.0
                dVdr = 0.0
                d2Vdr2 = 0.0
            end if
            return
        end subroutine d2repulsivePairPotential


        pure function cohesivePairPotential0( this,r ) result( phi )
    !---^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
    !*      returns the cohesive pair potential phi(r) ( eqn 27 )
            type(FinnisSinclair),intent(in)     ::      this
            real(kind=8),intent(in)                   ::      r
            real(kind=8)                              ::      phi
            real(kind=8)          ::      xx
            if (r < this%d) then
                xx = ( r - this%d )
                phi = xx*xx*( 1 + this%betaond*xx )
            else
                phi = 0.0
            end if
            return
        end function cohesivePairPotential0


        pure subroutine dcohesivePairPotential0( this,r , phi,dphidr )
    !---^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
    !*      returns the cohesive pair potential phi(r) ( eqn 27 )
    !*      and its derivative wrt r
            type(FinnisSinclair),intent(in)       ::      this
            real(kind=8),intent(in)                     ::      r
            real(kind=8),intent(out)                    ::      phi,dphidr
            real(kind=8)          ::      xx
            if (r < this%d) then
                xx = ( r - this%d )
                phi = xx*xx*( 1 + this%betaond*xx )
                dphidr = xx*( 2 + 3*this%betaond*xx )
            else
                phi    = 0.0
                dphidr = 0.0
            end if
            return
        end subroutine dcohesivePairPotential0

        pure subroutine d2cohesivePairPotential( this,r , phi,dphidr,d2phidr2 )
    !---^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
    !*      returns the cohesive pair potential phi(r) ( eqn 27 )
    !*      and its derivative wrt r
            type(FinnisSinclair),intent(in)       ::      this
            real(kind=8),intent(in)                     ::      r
            real(kind=8),intent(out)                    ::      phi,dphidr,d2phidr2
            real(kind=8)          ::      xx
            if (r < this%d) then
                xx = ( r - this%d )
                phi = xx*xx*( 1 + this%betaond*xx )
                dphidr = xx*( 2 + 3*this%betaond*xx )
                d2phidr2 = 2*(1 + 3*this%betaond*xx )
            else
                phi    = 0.0
                dphidr = 0.0
                d2phidr2 = 0.0
            end if
            return
        end subroutine d2cohesivePairPotential

!-------




!------------------------------------------------------------------------------


!-------        potential energy of ions



        function FinnisSinclair_atomic1(this, i, pkim) result(pe)
    !---^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
        !*  Constructs the potential energy of atom i
            type(FinnisSinclair), intent(inout)             ::  this
            integer,intent(in)                              ::  i
            !-- Transferred variables
            integer(kind=kim_intptr), intent(in) :: pkim

            real(kind=8)            ::  pe

            integer                 ::  ii,kk,nn
            real(kind=8)            ::  rho,rep,modrij,att
            real(kind=8),dimension(:,:),pointer                 ::  rij

            integer                 ::  nei1atom(1);    pointer(pnei1atom,nei1atom)
            real(kind=8)            ::  rij_(3,1);      pointer(pRij,Rij_)
            integer                 ::  ier,idum,atom_ret
            integer,parameter       ::  LOCATOR_MODE = 1


        !---   CALL TO NEIGHBOUR LIST FOR ATOM i
            ier = kim_api_get_neigh_f(pkim,LOCATOR_MODE,i,atom_ret,nn,pnei1atom,pRij)
            if (ier.lt.KIM_STATUS_OK) then
                idum = kim_api_report_error_f(__LINE__, THIS_FILE_NAME, &
                                              "kim_api_get_neigh_f", ier)
                return
            end if
            call KIM_to_F90_real_array_2d(Rij_,rij,3,nn)
        !---

            pe = 0.0
            rho = 0.0
            rep = 0.0
            do kk = 1,nn
                modrij = sqrt( rij(1,kk)*rij(1,kk) + rij(2,kk)*rij(2,kk) + rij(3,kk)*rij(3,kk) )
                rho  = rho + cohesivePairPotential( this,modrij )
                rep  = rep + repulsivePairPotential( this,modrij )
            end do
            att = bandEnergy(this,rho)
            pe = 0.5*rep + att
            return
        end function FinnisSinclair_atomic1


!-------    ionic contribution to force



        subroutine addForceFinnisSinclair1(this, i,force, pkim )
    !---^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
        !*  Calculates the force on a single atom "i"
            type(FinnisSinclair), intent(in)            ::  this
            integer,intent(in)                          ::  i
            real(kind=8),dimension(:,:),intent(inout)   ::  force

            !-- Transferred variables
            integer(kind=kim_intptr), intent(in)        :: pkim

            integer                     ::  nni
            integer                     ::  nei1atom(1);    pointer(pnei1atom,nei1atom)
            real(kind=8)                ::  rij_(3,1);      pointer(pRij,Rij_)
            integer                     ::  ier,idum,atom_ret
            integer,parameter           ::  LOCATOR_MODE = 1
            real(kind=8),dimension(:,:),pointer ::  rij
            integer,dimension(:),pointer        ::  neighbourj




        !---   CALL TO NEIGHBOUR LIST FOR ATOM i
            ier = kim_api_get_neigh_f(pkim,LOCATOR_MODE,i,atom_ret,nni,pnei1atom,pRij)
            if (ier.lt.KIM_STATUS_OK) then
                idum = kim_api_report_error_f(__LINE__, THIS_FILE_NAME, &
                                              "kim_api_get_neigh_f", ier)
                return
            end if
            call KIM_to_F90_real_array_2d(Rij_,rij,3,nni)
            call KIM_to_F90_int_array_1d(nei1atom,neighbourj,nni)

        !---
            call addForceFinnisSinclair2(this, i,rij,neighbourj,nni, force )
            return
        end subroutine addForceFinnisSinclair1



        subroutine addForceFinnisSinclair2(this, i,rij,neigh,nn, force )
    !---^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
        !*  Calculates the forces due a single atom i given its neighbour list
            type(FinnisSinclair), intent(in)            ::  this
            integer,intent(in)                          ::  i,nn
            real(kind=8),dimension(:,:),intent(in)      ::  rij
            integer,dimension(:),intent(in)             ::  neigh
            real(kind=8),dimension(:,:),intent(inout)   ::  force

            integer                     ::  ii,jj,kk
            real(kind=8)                ::  modrij, fij, V,dVdr, phi,dphidr,rho, EE,dEdrho
            real(kind=8),dimension(3)   ::  fi

        !---
            rho = 0.0
        !---    sum contributions to electron density
            do kk = 1,nn
                modrij = sqrt( rij(1,kk)*rij(1,kk) + rij(2,kk)*rij(2,kk) + rij(3,kk)*rij(3,kk) )
                rho = rho + cohesivePairPotential( this,modrij )
            end do

            call dbandEnergy( this,rho, EE,dEdrho )
            do kk = 1,nn

                modrij = sqrt( rij(1,kk)*rij(1,kk) + rij(2,kk)*rij(2,kk) + rij(3,kk)*rij(3,kk) )
            !---    repulsive contribution
                call drepulsivePairPotential( this,modrij , V,dVdr )
            !---    attractive contribution
                call dcohesivePairPotential( this,modrij , phi,dphidr )

                fi = (0.5*dVdr + dEdrho*dphidr)*rij(:,kk)/modrij
                force(:,i)  = force(:,i) + fi
                jj = neigh(kk)
                force(:,jj) = force(:,jj) - fi

            end do
            return
        end subroutine addForceFinnisSinclair2

!------------------------------------------------------------------------------

!-------

        pure function getA(this) result(A)
    !---^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
    !*      simple accessor for finnis-sinclair A
            type(FinnisSinclair),intent(in) ::      this
            real(kind=8)                          ::      A
            A = this%A
            return
        end function getA

        pure function getbeta(this) result(beta)
    !---^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
    !*      simple accessor for finnis-sinclair beta
            type(FinnisSinclair),intent(in) ::      this
            real(kind=8)                          ::      beta
            beta = this%betaond*this%d
            return
        end function getbeta

        pure function getd(this) result(d)
    !---^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
    !*      simple accessor for finnis-sinclair d
            type(FinnisSinclair),intent(in) ::      this
            real(kind=8)                          ::      d
            d = this%d
            return
        end function getd

        pure function getc(this) result(c)
    !---^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
    !*      simple accessor for finnis-sinclair c
            type(FinnisSinclair),intent(in) ::      this
            real(kind=8)                          ::      c
            c = this%c
            return
        end function getc

        pure function getc0(this) result(c0)
    !---^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
    !*      simple accessor for finnis-sinclair c0
            type(FinnisSinclair),intent(in) ::      this
            real(kind=8)                          ::      c0
            c0 = this%c0
            return
        end function getc0

        pure function getc1(this) result(c1)
    !---^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
    !*      simple accessor for finnis-sinclair c1
            type(FinnisSinclair),intent(in) ::      this
            real(kind=8)                          ::      c1
            c1 = this%c1
            return
        end function getc1

        pure function getc2(this) result(c2)
    !---^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
    !*      simple accessor for finnis-sinclair c2
            type(FinnisSinclair),intent(in) ::      this
            real(kind=8)                          ::      c2
            c2 = this%c2
            return
        end function getc2

        pure function getCutoffFinnisSinclair(this) result(c)
    !---^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
        !*  Returns the cutoff range
            type(FinnisSinclair), intent(in):: this
            real(kind=8) :: c
            c = max( this%c,this%d )
            return
        end function getCutoffFinnisSinclair



!------------------------------------------------------------------------------

!---    Here are the KIM API routines

!-------------------------------------------------------------------------------
!
! Model destroy routine
!
!-------------------------------------------------------------------------------

        integer function Destroy_FS(pkim)
    !---^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
            use KIM_API
            implicit none

            !-- Transferred variables
            integer(kind=kim_intptr), intent(in) :: pkim

            !-- Local variables
            real(kind=8),dimension(1)   ::      buffer; pointer(pbuffer,buffer)
            integer idum

            pbuffer = kim_api_get_model_buffer_f(pkim,Destroy_FS)
            if (Destroy_FS < KIM_STATUS_OK) then
               idum = kim_api_report_error_f(__LINE__, THIS_FILE_NAME, &
                                             "kim_api_get_model_buffer_f", Destroy_FS)
               return
            end if
            call free(pbuffer)

            Destroy_FS = KIM_STATUS_OK
            return
        end function Destroy_FS



!-------------------------------------------------------------------------------
!
! Compute energy and forces on atoms from the positions.
!
!-------------------------------------------------------------------------------
        integer function Compute_Energy_Forces_FS(pkim)
    !---^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
            implicit none

            !-- Transferred variables
            integer(kind=kim_intptr), intent(in)  :: pkim

            !-- Local variables
            integer         ::      ier
            integer         ::      ii
            real(kind=8)            ::      Ei

            !-- KIM variables
            integer numberOfParticles;      pointer(pnAtoms,numberOfParticles)
            real(kind=8)      ::  energy;         pointer(penergy,energy)
            real(kind=8)      ::  coordum(3,1);   pointer(pcoor,coordum)
            real(kind=8)      ::  forcedum(3,1);  pointer(pforce,forcedum)
            real(kind=8)      ::  enepotdum(1);   pointer(penepot,enepotdum)
            real(kind=8), pointer :: coor(:,:),force(:,:),ene_pot(:)
            integer comp_energy, comp_force, comp_enepot
            integer nei1atom(1);            pointer(pnei1atom,nei1atom)
            integer     ::  idum

            real(kind=8),dimension(1)   ::      buffer; pointer(pbuffer,buffer)
            real(kind=8), pointer       ::      buff(:)

            type(FinnisSinclair)        ::      fs



            pbuffer = kim_api_get_model_buffer_f(pkim,ier)
            if (ier < KIM_STATUS_OK) then
                idum = kim_api_report_error_f(__LINE__, THIS_FILE_NAME, &
                                              "kim_api_get_model_buffer_f", ier)
                goto 42
            end if
            call KIM_to_F90_real_array_1d(buffer,buff,7)

            fs = FinnisSinclair_ctor( buff(1),buff(2),buff(3),buff(4),buff(5),buff(6),buff(7) )


            ! Check to see if we have been asked to compute the energy, forces, energyperatom
            !
            call kim_api_getm_compute_f(pkim, ier, &
                 "energy",         comp_energy, 1, &
                 "forces",         comp_force,  1, &
                 "particleEnergy", comp_enepot, 1 )
            if (ier.lt.KIM_STATUS_OK) then
               idum = kim_api_report_error_f(__LINE__, THIS_FILE_NAME, &
                                             "kim_api_getm_compute_f", ier)
               goto 42
            end if



            ! Unpack data from KIM object
            !
            call kim_api_getm_data_f(pkim, ier,                       &
                 "numberOfParticles",   pnAtoms,         1,           &
                 "coordinates",         pcoor,           1,           &
                 "energy",              penergy,         comp_energy, &
                 "forces",              pforce,          comp_force,  &
                 "particleEnergy",      penepot,         comp_enepot )
            if (ier.lt.KIM_STATUS_OK) then
               idum = kim_api_report_error_f(__LINE__, THIS_FILE_NAME, &
                                             "kim_api_getm_data_f", ier)
               goto 42
            end if

            ! Cast to F90 arrays
            !
            call KIM_to_F90_real_array_2d(coordum,coor,3,numberOfParticles)
            if (comp_force.eq.1) &
               call KIM_to_F90_real_array_2d(forcedum,force,3,numberOfParticles)
            if (comp_enepot.eq.1) &
               call KIM_to_F90_real_array_1d(enepotdum,ene_pot,numberOfParticles)



            ! Initialize potential energies, forces, virial term
            !
            if (comp_enepot.eq.1) ene_pot(1:numberOfParticles) = 0.d0
            if (comp_energy.eq.1) energy = 0.d0
            if (comp_force.eq.1)  force(1:3,1:numberOfParticles) = 0.d0




        !---    compute energy
            if ( (comp_enepot == 1).and.(comp_energy == 1) ) then
                do ii = 1,numberOfParticles
                    Ei = ionicPotentialEnergy( fs , ii , pkim )
                    energy = energy + Ei
                    ene_pot(ii) = Ei
                end do
            else if ( (comp_enepot == 1).and.(comp_energy /= 1) ) then
                do ii = 1,numberOfParticles
                    Ei = ionicPotentialEnergy( fs , ii , pkim )
                    ene_pot(ii) = Ei
                end do
            else if ( (comp_enepot /= 1).and.(comp_energy == 1) ) then
                do ii = 1,numberOfParticles
                    Ei = ionicPotentialEnergy( fs , ii , pkim )
                    energy = energy + Ei
                end do
            end if


        !---    compute force
            if (comp_force.eq.1) then
                do ii = 1,numberOfParticles
                    call addForce( fs, ii, force , pkim )
                end do
            end if

            ier = KIM_STATUS_OK
42          continue
            Compute_Energy_Forces_FS = ier
            return
        end function Compute_Energy_Forces_FS





    end module TB_FinnisSinclair


!-------------------------------------------------------------------------------
!
! Model initialization routine (REQUIRED)
!
!-------------------------------------------------------------------------------
    integer function TB_FinnisSinclair_F__MD_669576659798_000_init(pkim , byte_paramfile, nmstrlen, numparamfiles)
!---^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
        use TB_FinnisSinclair
        use KIM_API
        implicit none

    !-- Transferred variables
        integer(kind=kim_intptr), intent(in) :: pkim
        integer,                  intent(in) :: nmstrlen
        integer,                  intent(in) :: numparamfiles
        integer(kind=1),          intent(in) :: byte_paramfile(nmstrlen*numparamfiles)


    !-- Local variables
        integer(kind=kim_intptr), parameter ::  one=1
        character(len=nmstrlen) ::  paramfile_names(numparamfiles)
        real(kind=8)            ::  cutoff;         pointer(pcutoff,cutoff)
        integer                 ::  ier, idum, return_error
        integer                 ::  i
        type(FinnisSinclair)    ::  fs
        real(kind=8)            ::  in_A,in_beta,in_d,in_c,in_c0,in_c1,in_c2

        real(kind=8),dimension(1)   ::  buffer; pointer(pbuffer,buffer)
        real(kind=8),pointer        ::  buff(:)

    !   assume all is well
        return_error = KIM_STATUS_OK

    !   generic code to process model parameter file names from byte string
        do i=0,numparamfiles-1
           write(paramfile_names(i+1),'(1000a)')  &
                char(byte_paramfile(i*nmstrlen+1: &
                                    i*nmstrlen+minloc(abs(byte_paramfile),dim=1)-1))
        enddo

    !   store pointers to public methods in KIM object
        call kim_api_setm_data_f(pkim, ier,                 &
            "compute", one, loc(Compute_Energy_Forces_FS), 1,  &
            "destroy", one, loc(Destroy_FS),               1)
        if (ier < KIM_STATUS_OK) then
            idum = kim_api_report_error_f(__LINE__, THIS_FILE_NAME, &
                                          "kim_api_set_data_f", ier)
            return_error = ier
            goto 1000
        end if

    !   Read in model parameters from parameter file
        open(10,file=paramfile_names(1),status="old")
        read(10,*,iostat=ier) in_A,in_beta,in_d,in_c,in_c0,in_c1,in_c2
        close(10)
        if (ier /= 0) then
            idum = kim_api_report_error_f(__LINE__, THIS_FILE_NAME, &
                                          "reading param file", ier)
            return_error = ier
            goto 1000
        end if

    !   store model cutoff in KIM object
        pcutoff =  kim_api_get_data_f(pkim,"cutoff",ier)
        if (ier < KIM_STATUS_OK) then
            idum = kim_api_report_error_f(__LINE__, THIS_FILE_NAME, &
                                          "kim_api_get_data_f", ier)
            return_error = ier
            goto 1000
        end if
        fs = FinnisSinclair_ctor( in_A,in_beta,in_d,in_c,in_c0,in_c1,in_c2 )
        cutoff = getCutoff(fs)


    !   store buffer to reconstruct Finnis Sinclair model
        allocate(buff(7))
        buff = (/ in_A,in_beta,in_d,in_c,in_c0,in_c1,in_c2 /)
        pbuffer = loc(buff)
        call kim_api_set_model_buffer_f(pkim,pbuffer,ier)
        if (ier < KIM_STATUS_OK) then
            idum = kim_api_report_error_f(__LINE__, THIS_FILE_NAME, &
                                          "kim_api_set_model_buffer_f", ier)
            return_error = ier
            goto 1000
        end if

1000    continue
        TB_FinnisSinclair_F__MD_669576659798_000_init = return_error
        return
    end function TB_FinnisSinclair_F__MD_669576659798_000_init
